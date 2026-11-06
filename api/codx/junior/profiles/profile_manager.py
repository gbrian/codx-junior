import os
import json
import pathlib
import logging
import re
import shutil

from typing import Any, Dict, List, Optional, Set

from codx.junior.settings import CODXJuniorSettings
from codx.junior.model.model import Profile
from codx.junior.utils.utils import write_file

from codx.junior.project.project_discover import (
    find_project_parents,
    find_project_by_name
)

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Project enrichment & profile knowledge
# -----------------------------------------------------------------------------
# A project can enrich a profile it does not own without editing the profile
# itself, through two per-project resources stored next to the profile folder:
#
#   <project .codx>/profiles/<Name>/enrich.md        -> extra instructions
#   <project .codx>/profiles/<Name>/knowledge/**     -> reference files
#
# The base (built-in) profile keeps its knowledge in
# `codx/junior/profiles/<Name>/knowledge/**`.
#
# Both resources are additive and optional: no file, no folder => the profile
# behaves exactly as before.
#
# NOTE: profile tools (`profile_learning`) are NOT handled here. They depend on
# the user and on the chat turn, so the agent (SmolAgent) decides whether to
# inject them into each request.
ENRICH_FILE_NAME = "enrich.md"
KNOWLEDGE_FOLDER_NAME = "knowledge"

# Enriched content is wrapped in invisible markers so `save_profile` can strip
# it back out: a composed content must never be persisted as the profile's own
# content.
ENRICH_BLOCK_PATTERN = re.compile(
    r"<!--\s*codx:enrich[^>]*-->.*?<!--\s*/codx:enrich\s*-->",
    re.DOTALL | re.IGNORECASE,
)

# Knowledge files are plain text resources: everything else is ignored so the
# tool never returns binary blobs.
TEXT_KNOWLEDGE_EXTENSIONS = {
    ".md", ".markdown", ".txt", ".rst",
    ".json", ".yaml", ".yml", ".csv", ".toml",
}

# Guardrail for reading: a knowledge file is injected into the model context.
MAX_KNOWLEDGE_FILE_SIZE = 512 * 1024

# Lines of context around a search hit.
EXCERPT_CONTEXT_LINES = 4

# -----------------------------------------------------------------------------
# Learned rules
# -----------------------------------------------------------------------------
# A profile learns in two ways:
#
#   * RULES -> short, always-relevant instructions stored as `## <title>`
#     blocks inside `<profiles>/<Name>/enrich.md`. They are composed into the
#     profile content, so they reach every chat prompt.
#   * FILES -> reference material stored in `<profiles>/<Name>/knowledge/**`,
#     indexed and retrieved on demand.
#
# A rule is addressed by its TITLE: writing the same title again replaces the
# block (instructions are never duplicated) and `forget` removes it. Rules are
# kept short on purpose because every rule costs prompt tokens on every chat.
RULE_HEADING_PATTERN = re.compile(r"^##\s+(?P<title>.+?)\s*$", re.MULTILINE)

# A single rule is injected into EVERY chat where the profile is active.
MAX_RULE_CHARS = 4000

# Beyond this amount the material must move to a knowledge file.
MAX_PROFILE_RULES = 40


def normalize_rule_title(title: str) -> str:
    """
    Normalize a rule title so the same instruction can be updated by title.

    :param title: Raw title.
    :return: Lower-cased, whitespace-collapsed title.
    """
    return " ".join((title or "").split()).casefold()


def slugify_rule_title(title: str) -> str:
    """
    Build a file name out of a rule title.

    :param title: Rule title.
    :return: Lower-case dash separated slug.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", (title or "").lower()).strip("-")
    return slug or "learned-rule"


def strip_profile_enrichment(content: str) -> str:
    """
    Remove every project enrichment block from a (possibly composed) content.

    :param content: Profile content, with or without enrichment blocks.
    :return: The content without enrichment blocks (the profile's own text).
    """
    return ENRICH_BLOCK_PATTERN.sub("", content or "").strip("\n")


def generate_llm_tree(root_path, indent="", is_last=True, ignore_list=None):
    if ignore_list is None:
        ignore_list = {'.git', '__pycache__', '.vscode', '.DS_Store', 'node_modules', 'venv'}
    
    path = pathlib.Path(root_path)
    if not path.exists():
        return "Invalid Path"

    # Header for the root on the first call
    tree_str = f"{indent}{'└── ' if is_last else '├── '}{path.name}/\n"
    
    # Update indent for children
    new_indent = indent + ("    " if is_last else "│   ")
    
    # Filter and sort items (directories first, then files)
    items = [i for i in path.iterdir() if i.name not in ignore_list]
    items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
    
    for i, item in enumerate(items):
        last_item = (i == len(items) - 1)
        if item.is_dir():
            tree_str += generate_llm_tree(item, new_indent, last_item, ignore_list)
        #else:
        #    connector = "└── " if last_item else "├── "
        #    tree_str += f"{new_indent}{connector}{item.name}\n"
            
    return tree_str

class ProfileManager:
    def __init__(self, settings: CODXJuniorSettings):
        self.settings = settings
        self.profiles_path = f"{settings.codx_path}/profiles"
        os.makedirs(self.profiles_path, exist_ok=True)

        current_file_path = os.path.abspath(__file__)
        current_directory = os.path.dirname(current_file_path)
        self.base_profiles_path = f"{current_directory}"

        # Cache of the project inheritance chain (parents -> this project)
        self._profile_chain_cache: Optional[List["ProfileManager"]] = None

    def base_profiles(self):
        def _files (file_gen):
            return [str(file) for file in file_gen]

        base_profiles = _files(pathlib.Path(self.base_profiles_path).rglob("**/*.profile"))
        return _files(base_profiles)

    def _base_profile_path(self, profile_name: str) -> Optional[str]:
        """
        Return the file path of a built-in profile (new folder or old flat form).

        :param profile_name: Profile name.
        :return: Absolute path of the built-in profile, or None.
        """
        name = str(profile_name or "").strip().lstrip("@")
        if not name or name != os.path.basename(name) or name in {".", ".."}:
            return None
        for path in (
            os.path.join(self.base_profiles_path, name, f"{name}.profile"),
            os.path.join(self.base_profiles_path, f"{name}.profile"),
        ):
            if os.path.isfile(path):
                return path
        return None

    def project_profile_paths(self):
        def _files (file_gen):
            return [str(file) for file in file_gen]

        # Look for profiles in both old format (flat) and new format (in folders)
        profiles = []
        # New format: [profile_name]/[profile_name].profile
        profiles.extend(_files(list(pathlib.Path(self.profiles_path).rglob("*/*.profile"))))
        # Old format fallback: *.profile (for backward compatibility)
        profiles.extend(_files(list(pathlib.Path(self.profiles_path).glob("*.profile"))))
        
        return profiles

    # -------------------------------------------------------------------------
    # Profile inheritance chain (project -> parents -> codx-junior)
    # -------------------------------------------------------------------------
    def profile_chain(self) -> List["ProfileManager"]:
        """
        Return the profile managers of this project's inheritance chain.

        Order: outermost parent first, then every intermediate project, and
        this project last (the most specific level). ``codx-junior`` is added as
        a regular level, exactly like :meth:`list_all_profiles` does, and
        duplicates are dropped.

        The chain is cached per instance: composing a profile reads it on every
        read path (list, read, chat composition).

        :return: ProfileManagers, outermost parent -> this project.
        """
        if self._profile_chain_cache is not None:
            return self._profile_chain_cache

        seen_ids = {self.settings.project_id}
        chain: List["ProfileManager"] = []

        parents = list(find_project_parents(project=self.settings))
        codx_junior = find_project_by_name("codx-junior")
        if codx_junior and codx_junior.project_id not in seen_ids:
            parents.append(codx_junior)

        # Shortest path first => outermost parent first.
        parents.sort(key=lambda project: len(project.project_path or ""))

        for project in parents:
            if project.project_id in seen_ids:
                continue
            seen_ids.add(project.project_id)
            chain.append(ProfileManager(settings=project))

        chain.append(self)
        self._profile_chain_cache = chain
        return chain

    def owns_profile(self, profile_name: str) -> bool:
        """
        Return True when THIS level defines the profile (a new line).

        A level defining ``<Name>.profile`` owns the profile: it does not
        inherit the enrichment of the levels above it.

        :param profile_name: Profile name.
        :return: True when the profile is defined at this level.
        """
        if not profile_name:
            return False
        folder_profile = os.path.join(
            self.profiles_path, profile_name, f"{profile_name}.profile"
        )
        flat_profile = os.path.join(self.profiles_path, f"{profile_name}.profile")
        return os.path.isfile(folder_profile) or os.path.isfile(flat_profile)

    def profile_exists(self, profile_name: str) -> bool:
        """
        Return True when the profile is visible from this project.

        :param profile_name: Profile name.
        :return: True for project, inherited or built-in profiles.
        """
        name = str(profile_name or "").strip().lstrip("@")
        if not name or name != os.path.basename(name) or name in {".", ".."}:
            return False
        if self._base_profile_path(name):
            return True
        return any(manager.owns_profile(name) for manager in self.profile_chain())

    def profile_enrich_path(self, profile_name: str) -> str:
        """
        Path of the enrichment file of a profile at THIS level.

        It lives inside the profile folder (``<Name>/enrich.md``), so it can
        never be confused with the profile's own content (``<Name>/<Name>.md``).

        :param profile_name: Profile name.
        :return: Absolute path to the enrichment markdown file.
        """
        return os.path.join(self.profiles_path, profile_name, ENRICH_FILE_NAME)

    def profile_knowledge_path(self, profile_name: str) -> str:
        """
        Knowledge folder of a profile at THIS level.

        :param profile_name: Profile name.
        :return: Absolute path to ``<profiles>/<Name>/knowledge``.
        """
        return os.path.join(
            self.profiles_path, profile_name, KNOWLEDGE_FOLDER_NAME
        )

    def base_profile_knowledge_path(self, profile_name: str) -> str:
        """
        Knowledge folder of the built-in (base) profile.

        :param profile_name: Profile name.
        :return: Absolute path to ``codx/junior/profiles/<Name>/knowledge``.
        """
        return os.path.join(
            self.base_profiles_path, profile_name, KNOWLEDGE_FOLDER_NAME
        )

    @staticmethod
    def _read_text(path: str, max_size: int = MAX_KNOWLEDGE_FILE_SIZE) -> str:
        """
        Read a text file, returning an empty string when it cannot be used.

        :param path: File path.
        :param max_size: Files bigger than this are skipped.
        :return: File content (empty string on error or when missing).
        """
        try:
            if not os.path.isfile(path):
                return ""
            if os.path.getsize(path) > max_size:
                logger.warning("Skipping oversized profile resource: %s", path)
                return ""
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as ex:
            logger.warning("Could not read profile resource '%s': %s", path, ex)
            return ""

    @staticmethod
    def _wrap_enrichment(project_name: str, text: str) -> str:
        """
        Wrap enrichment text in the markers used to strip it on save.

        :param project_name: Project the enrichment comes from.
        :param text: Enrichment markdown.
        :return: Marked block.
        """
        return "\n".join([
            f"<!-- codx:enrich project={project_name or 'project'} -->",
            text.strip("\n"),
            "<!-- /codx:enrich -->",
        ])

    def compose_profile_content(self, profile: Profile) -> str:
        """
        Build the effective content of a profile for THIS project.

        Composition = the profile's own content + the enrichment of every level
        between the level that owns the profile and this project (outermost
        first). A level that defines the profile starts a new line, so it never
        receives enrichment from above.

        When no level has an enrichment file, the content is returned untouched.

        :param profile: Profile loaded by :meth:`load_profile` (own content).
        :return: Composed content (own content when there is no enrichment).
        """
        if not profile or not profile.name:
            return profile.content or ""

        own_content = (profile.content or "").strip("\n")

        chain = self.profile_chain()
        owner_index = -1
        for index, manager in enumerate(chain):
            if manager.owns_profile(profile.name):
                owner_index = index

        blocks: List[str] = []
        for manager in chain[owner_index + 1:]:
            enrich_path = manager.profile_enrich_path(profile.name)
            text = self._read_text(enrich_path).strip("\n")
            if not text:
                continue
            blocks.append(self._wrap_enrichment(manager.settings.project_name, text))

        if not blocks:
            return profile.content or ""

        parts = ([own_content] if own_content else []) + blocks
        return "\n\n".join(parts)

    def list_all_profiles(self):
        parent_projects = find_project_parents(project=self.settings)
        codx_junior = find_project_by_name("codx-junior")
        if codx_junior:
            parent_projects.append(codx_junior)
        logger.info("list_all_profiles: %s", [p.project_name for p in parent_projects])
        
        all_profiles = {}
        
        # 1. Parent and codx-junior project profiles
        for project in parent_projects:
            profiles = ProfileManager(settings=project).list_profiles()
            for profile in profiles:
                all_profiles[profile.name] = profile
        
        # 2. Current project profiles (can override parent profiles)
        for profile in self.list_profiles():
            all_profiles[profile.name] = profile

        # 3. Built-in base profiles from source code (only if not already defined)
        for profile_path in self.base_profiles():
            profile = self.load_profile(profile_path)
            if profile and profile.name not in all_profiles:
                all_profiles[profile.name] = profile
        
        return [self.get_profile_With_content(profile=p) for p in list(all_profiles.values())]


    def list_profiles(self):
        profiles = [self.load_profile(profile_path) for profile_path in self.project_profile_paths()]
        return [p for p in profiles if p is not None]

    def read_profile(self, profile_name) -> Profile:
        """
        Read one profile visible from this project.

        Resolution order:

        1. the project profile (new ``<Name>/<Name>.profile`` folder format,
           then the legacy flat ``<Name>.profile``),
        2. the built-in (base) profile from the source tree.

        The match is exact by name: the old implementation searched the profile
        name inside the whole path, which could resolve an unrelated profile
        (a folder containing the name) and never found a built-in profile.

        :param profile_name: Profile name (``@`` prefix accepted).
        :return: The composed profile (own content + project enrichment), or
                 None when no profile with that name exists.
        """
        name = str(profile_name or "").strip().lstrip("@")
        if not name:
            return None
        if name != pathlib.Path(name).name or name in {".", ".."}:
            return None

        profile = None
        for profile_path in (
            os.path.join(self.profiles_path, name, f"{name}.profile"),
            os.path.join(self.profiles_path, f"{name}.profile"),
        ):
            if os.path.isfile(profile_path):
                profile = self.load_profile(profile_path)
                break

        if profile is None:
            base_path = self._base_profile_path(name)
            if base_path:
                profile = self.load_profile(base_path)

        if profile is None:
            return None
        # Composed content: callers never need to know about project enrichment.
        return self.get_profile_With_content(profile=profile)

    def load_profile(self, profile_path) -> Profile:
        """
        Load a profile from disk returning its OWN content (no enrichment).

        This is the private building block: :meth:`read_profile` and
        :meth:`get_profile_With_content` compose the project enrichment on top.

        :param profile_path: Path of the ``<Name>.profile`` JSON file.
        :return: The loaded profile (or a minimal valid one on error).
        """
        profile = None
        try:
            with open(profile_path, 'r') as f:
                content = f.read()
                
                # Validate content is not empty
                if not content or not content.strip():
                    logger.warning(f"Profile file is empty, using defaults: {profile_path}")
                    profile = Profile(name=pathlib.Path(profile_path).stem)
                else:
                    try:
                        profile = Profile(**json.loads(content))
                    except json.JSONDecodeError as json_ex:
                        logger.error(f"Invalid JSON in profile {profile_path}: {json_ex}. Using defaults.")
                        profile = Profile(name=pathlib.Path(profile_path).stem)
                
                profile.path = profile_path

            # Load content from markdown file in new format: [profile_name]/[profile_name].md
            profile_dir = os.path.dirname(profile_path)
            markdown_content_path = os.path.join(profile_dir, f"{profile.name}.md")
            
            if os.path.isfile(markdown_content_path):
                with open(markdown_content_path, 'r') as f:
                    profile.content = f.read()
                # logger.info(f"Loaded profile content from: {markdown_content_path}")
            
            if not profile.avatar:
                profile.avatar = f"https://gravatar.com/avatar/baa8db8ab2afb7ababc235269e762662?s=400&d=robohash&r={profile.name}"
            profile.project_id = self.settings.project_id
            return profile
        except Exception as ex:
            logger.exception(f"Error loading profile: {profile_path} {ex}")
            # Return a minimal valid profile instead of raising
            return Profile(
                name=pathlib.Path(profile_path).stem,
                path=profile_path,
                project_id=self.settings.project_id,
                avatar=f"https://gravatar.com/avatar/baa8db8ab2afb7ababc235269e762662?s=400&d=robohash&r={pathlib.Path(profile_path).stem}"
            )

    def _migrate_profile_to_folder(self, profile_name: str, old_profile_path: str):
        """Migrate a profile from flat structure to folder structure"""
        profile_folder = os.path.join(self.profiles_path, profile_name)
        os.makedirs(profile_folder, exist_ok=True)
        
        new_profile_path = os.path.join(profile_folder, f"{profile_name}.profile")
        
        # Move profile JSON file
        if os.path.isfile(old_profile_path) and old_profile_path != new_profile_path:
            shutil.move(old_profile_path, new_profile_path)
            logger.info(f"Migrated profile from {old_profile_path} to {new_profile_path}")
        
        # Move associated markdown content file (old format: [profile_name].md.profile or [profile_name].profile.md)
        old_markdown_paths = [
            f"{old_profile_path.replace('.profile', '')}.md.profile",
            f"{old_profile_path.replace('.profile', '')}.profile.md"
        ]
        
        for old_markdown_path in old_markdown_paths:
            if os.path.isfile(old_markdown_path):
                new_markdown_path = os.path.join(profile_folder, f"{profile_name}.md")
                shutil.move(old_markdown_path, new_markdown_path)
                logger.info(f"Migrated markdown content from {old_markdown_path} to {new_markdown_path}")
                break

    def save_profile(self, profile: Profile):
        if not profile.name:
            raise Exception('Invalid profile')

        # Create profile folder
        profile_folder = os.path.join(self.profiles_path, profile.name)
        os.makedirs(profile_folder, exist_ok=True)
        
        # New profile path in folder structure
        profile_path = os.path.join(profile_folder, f"{profile.name}.profile")
        
        logger.info(f"Save profile {profile_path}")
        
        # Check if profile exists in old flat format and migrate it
        old_profile_path = os.path.join(self.profiles_path, f"{profile.name}.profile")
        if os.path.isfile(old_profile_path) and old_profile_path != profile_path:
            self._migrate_profile_to_folder(profile.name, old_profile_path)
        
        # Save profile content to markdown file in new format: [profile_name]/[profile_name].md
        # The project enrichment blocks are never persisted: the content written
        # is always the profile's own content.
        if profile.content:
            markdown_content_path = os.path.join(profile_folder, f"{profile.name}.md")
            with open(markdown_content_path, 'w') as f:
                f.write(strip_profile_enrichment(profile.content))
            logger.info(f"Saved profile content to: {markdown_content_path}")
        
        # Save profile JSON without content property
        with open(profile_path, 'w') as f:
            profile_data = profile.model_dump()
            profile_data['content'] = None
            profile_data['parsed_content'] = None
            f.write(json.dumps(profile_data, indent=2))

    def delete_profile(self, profile_name):
        # Delete profile in new folder structure
        profile_folder = os.path.join(self.profiles_path, profile_name)
        if os.path.isdir(profile_folder):
            shutil.rmtree(profile_folder)
            logger.info(f"Deleted profile folder: {profile_folder}")
        
        # Also check and delete old flat format (backward compatibility)
        old_profile_path = os.path.join(self.profiles_path, f"{profile_name}.profile")
        if os.path.isfile(old_profile_path):
            os.remove(old_profile_path)
            logger.info(f"Deleted old format profile: {old_profile_path}")
            
            old_markdown_paths = [
                f"{old_profile_path.replace('.profile', '')}.md.profile",
                f"{old_profile_path.replace('.profile', '')}.profile.md"
            ]
            for old_markdown_path in old_markdown_paths:
                if os.path.isfile(old_markdown_path):
                    os.remove(old_markdown_path)
                    logger.info(f"Deleted old format markdown: {old_markdown_path}")

    # -------------------------------------------------------------------------
    # Learned rules: short instructions stored in `enrich.md`
    # -------------------------------------------------------------------------
    @staticmethod
    def _parse_rules(content: str) -> List[Dict[str, str]]:
        """
        Split an enrichment file into its ``## <title>`` rule blocks.

        :param content: Enrichment markdown.
        :return: ``{"title", "content"}`` dicts, file order preserved.
        """
        content = content or ""
        headings = list(RULE_HEADING_PATTERN.finditer(content))

        rules: List[Dict[str, str]] = []
        for index, heading in enumerate(headings):
            start = heading.end()
            end = headings[index + 1].start() if index + 1 < len(headings) else len(content)
            rules.append({
                "title": heading.group("title").strip(),
                "content": content[start:end].strip("\n"),
            })
        return rules

    @staticmethod
    def _render_rules(rules: List[Dict[str, str]]) -> str:
        """
        Render parsed rules back into the enrichment markdown format.

        :param rules: ``{"title", "content"}`` dicts.
        :return: Enrichment file content (empty string when no rules).
        """
        blocks = [
            f"## {rule['title']}\n\n{rule['content'].strip()}".strip()
            for rule in rules
            if (rule.get("title") or "").strip()
        ]
        return ("\n\n".join(blocks).strip() + "\n") if blocks else ""

    def profile_rules(
        self,
        profile_name: str,
        include_inherited: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List the learned rules of a profile for this project.

        Rules come from the ``enrich.md`` of every level between the level that
        owns the profile and this project (outermost first). Only the rules of
        THIS project are editable: parent and base rules are inherited and
        read-only.

        :param profile_name: Profile name.
        :param include_inherited: Include the rules learned by parent levels.
        :return: ``{"title", "content", "source", "path", "editable"}`` dicts.
        """
        if not profile_name:
            return []

        chain = self.profile_chain()
        owner_index = -1
        for index, manager in enumerate(chain):
            if manager.owns_profile(profile_name):
                owner_index = index

        rules: List[Dict[str, Any]] = []
        for manager in chain[owner_index + 1:]:
            editable = manager.settings.project_id == self.settings.project_id
            if not include_inherited and not editable:
                continue
            path = manager.profile_enrich_path(profile_name)
            for rule in self._parse_rules(self._read_text(path)):
                rules.append({
                    "title": rule["title"],
                    "content": rule["content"],
                    "source": manager.settings.project_name or "project",
                    "path": path,
                    "editable": editable,
                })
        return rules

    def find_profile_rule(
        self,
        profile_name: str,
        title: str,
        editable_only: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Find a learned rule by title.

        :param profile_name: Profile name.
        :param title: Rule title (case/whitespace insensitive).
        :param editable_only: Only consider rules learned by this project.
        :return: The matching rule, or None.
        """
        wanted = normalize_rule_title(title)
        if not wanted:
            return None
        # Rules are listed outermost first: reversed() takes the most specific
        # (closest to this project) match first.
        for rule in reversed(self.profile_rules(profile_name)):
            if normalize_rule_title(rule["title"]) != wanted:
                continue
            if editable_only and not rule["editable"]:
                continue
            return rule
        return None

    def upsert_profile_rule(
        self,
        profile_name: str,
        title: str,
        text: str
    ) -> Dict[str, Any]:
        """
        Learn (create or replace) a RULE in this project's profile enrichment.

        A rule is a short instruction that is composed into the profile content
        and therefore reaches every chat. Writing an existing title replaces its
        block, so instructions are never duplicated.

        :param profile_name: Profile being enriched.
        :param title: Rule title (its identifier inside ``enrich.md``).
        :param text: Markdown instructions.
        :return: ``{"path", "title", "created", "rules"}``.

        :raises ValueError: On invalid input or when the rule budget is full.
        """
        profile_name = (profile_name or "").strip()
        title = " ".join((title or "").split()).strip()
        text = (text or "").strip()

        if not profile_name:
            raise ValueError("profile_name is required")
        if not title:
            raise ValueError(
                "title is required: it is the identifier used to update or "
                "forget the rule later"
            )
        if not text:
            raise ValueError("content is required: write the instruction to remember")
        if len(text) > MAX_RULE_CHARS:
            raise ValueError(
                f"The rule has {len(text)} characters; a rule holds at most "
                f"{MAX_RULE_CHARS} because it is injected into every chat. Store "
                "the long material as a knowledge file instead."
            )
        if not self.profile_exists(profile_name):
            raise ValueError(
                f"Unknown profile '{profile_name}': it does not exist in this "
                "project, in a parent project or in the base profiles."
            )

        enrich_path = self.profile_enrich_path(profile_name)
        os.makedirs(os.path.dirname(enrich_path), exist_ok=True)

        rules = self._parse_rules(self._read_text(enrich_path))
        wanted = normalize_rule_title(title)
        existing_titles = [normalize_rule_title(rule["title"]) for rule in rules]
        created = wanted not in existing_titles

        if created and len(rules) >= MAX_PROFILE_RULES:
            raise ValueError(
                f"Profile '{profile_name}' already has {len(rules)} rules (max "
                f"{MAX_PROFILE_RULES}). Promote or forget some of them, or store "
                "this content as a knowledge file."
            )

        rules = [
            rule for rule in rules
            if normalize_rule_title(rule["title"]) != wanted
        ]
        rules.append({"title": title, "content": text})

        with open(enrich_path, "w", encoding="utf-8") as f:
            f.write(self._render_rules(rules))

        logger.info(
            "Profile '%s' %s rule '%s' in project '%s' (%s)",
            profile_name,
            "created" if created else "updated",
            title,
            self.settings.project_name,
            enrich_path,
        )
        return {
            "path": enrich_path,
            "title": title,
            "created": created,
            "rules": len(rules),
        }

    def delete_profile_rule(self, profile_name: str, title: str) -> str:
        """
        Forget a rule learned by THIS project.

        Inherited rules (parent projects and base profile) are read-only: they
        can only be removed from the level that learned them.

        :param profile_name: Profile name.
        :param title: Rule title.
        :return: Path of the enrichment file.

        :raises ValueError: If the rule is not found at this level.
        """
        profile_name = (profile_name or "").strip()
        if not profile_name:
            raise ValueError("profile_name is required")

        wanted = normalize_rule_title(title)
        if not wanted:
            raise ValueError("title is required: the rule identifier to forget")

        enrich_path = self.profile_enrich_path(profile_name)
        rules = self._parse_rules(self._read_text(enrich_path))
        kept = [
            rule for rule in rules
            if normalize_rule_title(rule["title"]) != wanted
        ]

        if len(kept) == len(rules):
            raise ValueError(
                f"Rule '{title}' was not learned by project "
                f"'{self.settings.project_name}'; inherited rules are read-only."
            )

        with open(enrich_path, "w", encoding="utf-8") as f:
            f.write(self._render_rules(kept))

        logger.info(
            "Profile '%s' forgot rule '%s' in project '%s'",
            profile_name,
            title,
            self.settings.project_name,
        )
        return enrich_path

    def profile_knowledge_overview(self, profile_name: str) -> Dict[str, Any]:
        """
        Summarize everything a profile has learned for this project.

        Used by the ``overview`` action of the ``profile_learning`` tool so the
        model can decide what to read, forget or promote.

        :param profile_name: Profile name.
        :return: Rules, knowledge files, writable locations and limits.
        """
        rules = self.profile_rules(profile_name)
        files = self.list_profile_knowledge(profile_name)
        enrich_path = self.profile_enrich_path(profile_name)
        own_rules = [rule for rule in rules if rule["editable"]]

        return {
            "profile": profile_name,
            "rules": rules,
            "rules_count": len(rules),
            "own_rules_count": len(own_rules),
            "rules_chars": sum(len(rule["content"]) for rule in rules),
            "rules_file": enrich_path,
            "rules_file_exists": os.path.isfile(enrich_path),
            "knowledge_files": files,
            "knowledge_folder": self.profile_knowledge_path(profile_name),
            "limits": {
                "max_rule_chars": MAX_RULE_CHARS,
                "max_rules": MAX_PROFILE_RULES,
            },
        }

    # -------------------------------------------------------------------------
    # Knowledge files
    # -------------------------------------------------------------------------
    def profile_knowledge_roots(self, profile_name: str) -> List[Dict[str, str]]:
        """
        Resolve every knowledge folder visible for a profile, in chain order.

        Order: built-in base, then the project levels from the outermost parent
        down to this project. Missing folders are skipped.

        :param profile_name: Profile name.
        :return: List of ``{"source", "path"}`` dicts.
        """
        if not profile_name:
            return []

        roots: List[Dict[str, str]] = [{
            "source": "base",
            "path": self.base_profile_knowledge_path(profile_name),
        }]
        for manager in self.profile_chain():
            roots.append({
                "source": manager.settings.project_name or "project",
                "path": manager.profile_knowledge_path(profile_name),
            })
        return [root for root in roots if os.path.isdir(root["path"])]

    def list_profile_knowledge(self, profile_name: str) -> List[Dict[str, Any]]:
        """
        List the text knowledge files available for a profile.

        :param profile_name: Profile name.
        :return: List of ``{source, path, file, size}`` dicts.
        """
        files: List[Dict[str, Any]] = []
        for root in self.profile_knowledge_roots(profile_name):
            for file_path in sorted(pathlib.Path(root["path"]).rglob("*")):
                if not file_path.is_file():
                    continue
                if file_path.suffix.lower() not in TEXT_KNOWLEDGE_EXTENSIONS:
                    continue
                files.append({
                    "source": root["source"],
                    "path": str(file_path),
                    "file": os.path.relpath(str(file_path), root["path"]),
                    "size": file_path.stat().st_size,
                })
        return files

    def _resolve_knowledge_file(
        self,
        profile_name: str,
        file_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find a knowledge file by its relative path within its knowledge folder.

        :param profile_name: Profile name.
        :param file_name: Path relative to the knowledge folder.
        :return: The matching entry, or None.
        """
        wanted = (file_name or "").strip().replace("\\", "/").lstrip("/")
        if not wanted:
            return None
        for entry in self.list_profile_knowledge(profile_name):
            if entry["file"].replace("\\", "/") == wanted:
                return entry
        return None

    def read_profile_knowledge(self, profile_name: str, file_name: str) -> str:
        """
        Read one knowledge file of a profile (base or any project level).

        :param profile_name: Profile name.
        :param file_name: Path relative to the knowledge folder.
        :return: File content.

        :raises ValueError: If the file is not found.
        """
        entry = self._resolve_knowledge_file(profile_name, file_name)
        if not entry:
            raise ValueError(
                f"Knowledge file '{file_name}' not found for profile "
                f"'{profile_name}'."
            )
        return self._read_text(entry["path"])

    def save_profile_knowledge(
        self,
        profile_name: str,
        file_name: str,
        content: str,
        overwrite: bool = False
    ) -> str:
        """
        Create or update a knowledge file for a profile in THIS project.

        Knowledge always lands in the current project, so a project can keep its
        own reference material without touching the base profile.

        :param profile_name: Profile name.
        :param file_name: Path relative to the knowledge folder.
        :param content: File content.
        :param overwrite: Replace the file when it already exists.
        :return: Path of the written file.

        :raises ValueError: On invalid input or unexpected overwrite.
        """
        profile_name = (profile_name or "").strip()
        if not profile_name:
            raise ValueError("profile_name is required")
        if not self.profile_exists(profile_name):
            raise ValueError(f"Unknown profile '{profile_name}'.")
        if content is None or not str(content).strip():
            raise ValueError("content is required")

        relative_path = self._validate_knowledge_file_name(file_name)
        knowledge_path = self.profile_knowledge_path(profile_name)
        target_path = os.path.join(knowledge_path, relative_path)

        if os.path.isfile(target_path) and not overwrite:
            raise ValueError(
                f"Knowledge file '{relative_path}' already exists for profile "
                f"'{profile_name}'. Read it first and use overwrite=True to "
                "replace it."
            )

        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(str(content))

        logger.info(
            "Profile '%s' knowledge saved by project '%s': %s",
            profile_name,
            self.settings.project_name,
            target_path,
        )
        return target_path

    def delete_profile_knowledge(self, profile_name: str, file_name: str) -> str:
        """
        Delete a knowledge file of THIS project's profile knowledge folder.

        Base and parent knowledge folders are read-only: only the current
        project's files can be deleted.

        :param profile_name: Profile name.
        :param file_name: Path relative to the knowledge folder.
        :return: Path of the deleted file.

        :raises ValueError: If the file is not owned by this project.
        """
        relative_path = self._validate_knowledge_file_name(file_name)
        knowledge_path = self.profile_knowledge_path(profile_name)
        target_path = os.path.join(knowledge_path, relative_path)

        if not os.path.isfile(target_path):
            raise ValueError(
                f"Knowledge file '{relative_path}' does not exist in this "
                f"project for profile '{profile_name}'. Base and parent "
                "knowledge files are read-only."
            )

        os.remove(target_path)
        logger.info(
            "Profile '%s' knowledge deleted: %s", profile_name, target_path
        )
        return target_path

    @staticmethod
    def _validate_knowledge_file_name(file_name: str) -> str:
        """
        Validate a knowledge file name (relative, text extension only).

        :param file_name: Candidate relative path.
        :return: Validated relative path (``.md`` added when missing).

        :raises ValueError: If the path escapes the knowledge folder or the
            extension is not a text one.
        """
        name = (file_name or "").strip().replace("\\", "/").lstrip("/")
        if not name:
            raise ValueError("file_name is required")
        if ".." in name.split("/"):
            raise ValueError(f"file_name cannot contain '..': {file_name!r}")
        if not os.path.splitext(name)[1]:
            name = f"{name}.md"
        extension = os.path.splitext(name)[1].lower()
        if extension not in TEXT_KNOWLEDGE_EXTENSIONS:
            raise ValueError(
                f"Unsupported knowledge file extension '{extension}'. Allowed: "
                f"{', '.join(sorted(TEXT_KNOWLEDGE_EXTENSIONS))}"
            )
        return name

    def search_profile_knowledge(
        self,
        profile_name: str,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search the profile knowledge folders (base + every project level).

        The search is a plain case-insensitive term match on the filesystem: no
        indexing is required, so a file is searchable as soon as it is written.
        It is the fallback used when the semantic index is not available.

        :param profile_name: Profile name.
        :param query: Search terms (whitespace separated, OR matched).
        :param limit: Maximum number of files returned.
        :return: Matching entries with ``matches`` count and an ``excerpt``.
        """
        terms = [term for term in re.split(r"\s+", (query or "").strip().lower()) if term]
        if not terms:
            raise ValueError("query is required")

        limit = max(1, min(int(limit or 10), 50))
        results: List[Dict[str, Any]] = []

        for entry in self.list_profile_knowledge(profile_name):
            text = self._read_text(entry["path"])
            if not text:
                continue
            lines = text.splitlines()
            hits = [
                index for index, line in enumerate(lines)
                if any(term in line.lower() for term in terms)
            ]
            if not hits:
                continue
            start = max(hits[0] - EXCERPT_CONTEXT_LINES, 0)
            end = min(hits[0] + EXCERPT_CONTEXT_LINES + 1, len(lines))
            results.append({
                **entry,
                "matches": len(hits),
                "excerpt": "\n".join(lines[start:end]).strip(),
            })

        results.sort(key=lambda result: result["matches"], reverse=True)
        return results[:limit]

    # -------------------------------------------------------------------------
    # Promotion: decide between a rule (prompt) and a knowledge file (index)
    # -------------------------------------------------------------------------
    def promote_profile_rule_to_knowledge(
        self,
        profile_name: str,
        title: str,
        file_name: Optional[str] = None,
        delete_rule: bool = True
    ) -> Dict[str, Any]:
        """
        Move a learned rule into an indexed knowledge file.

        Used when a rule grew too long (or too specific) to stay in the prompt of
        every chat: the content becomes a knowledge file, retrieved on demand,
        and the rule is removed unless ``delete_rule`` is False.

        :param profile_name: Profile name.
        :param title: Title of a rule learned by this project.
        :param file_name: Target knowledge file (defaults to a slug of the title).
        :param delete_rule: Forget the rule after writing the file.
        :return: ``{"profile", "title", "file", "path", "rule_deleted"}``.

        :raises ValueError: When the rule does not exist at this level.
        """
        profile_name = (profile_name or "").strip()
        if not profile_name:
            raise ValueError("profile_name is required")

        rule = self.find_profile_rule(profile_name, title, editable_only=True)
        if not rule:
            raise ValueError(
                f"Rule '{title}' was not learned by project "
                f"'{self.settings.project_name}'. Inherited rules are read-only: "
                "promote them from the project that owns them."
            )

        relative_path = self._validate_knowledge_file_name(
            file_name or f"{slugify_rule_title(rule['title'])}.md"
        )
        content = f"# {rule['title']}\n\n{rule['content'].strip()}\n"
        path = self.save_profile_knowledge(
            profile_name=profile_name,
            file_name=relative_path,
            content=content,
            overwrite=True,
        )

        if delete_rule:
            self.delete_profile_rule(profile_name=profile_name, title=rule["title"])

        logger.info(
            "Profile '%s' promoted rule '%s' to knowledge file '%s'",
            profile_name,
            rule["title"],
            relative_path,
        )
        return {
            "profile": profile_name,
            "title": rule["title"],
            "file": relative_path,
            "path": path,
            "rule_deleted": bool(delete_rule),
        }

    def promote_profile_knowledge_to_rule(
        self,
        profile_name: str,
        file_name: str,
        title: Optional[str] = None,
        delete_file: bool = True
    ) -> Dict[str, Any]:
        """
        Turn a (short) knowledge file into a rule.

        Used when a document is really a durable instruction that must be present
        in every chat. The content must fit in a rule, otherwise it must be
        summarised first.

        :param profile_name: Profile name.
        :param file_name: Knowledge file path relative to the knowledge folder.
        :param title: Rule title (defaults to the file name).
        :param delete_file: Delete the file after learning the rule.
        :return: ``{"profile", "title", "path", "file_deleted"}``.

        :raises ValueError: When the file is missing or too long for a rule.
        """
        profile_name = (profile_name or "").strip()
        if not profile_name:
            raise ValueError("profile_name is required")

        content = self.read_profile_knowledge(
            profile_name=profile_name, file_name=file_name
        ).strip()

        if len(content) > MAX_RULE_CHARS:
            raise ValueError(
                f"'{file_name}' has {len(content)} characters; a rule holds at "
                f"most {MAX_RULE_CHARS} because it is injected into every chat. "
                "Summarise it into a short imperative rule and keep the file for "
                "the detail."
            )

        rule_title = (title or "").strip() or self._rule_title_from_file(file_name)
        result = self.upsert_profile_rule(
            profile_name=profile_name, title=rule_title, text=content
        )

        deleted = False
        if delete_file:
            try:
                self.delete_profile_knowledge(
                    profile_name=profile_name, file_name=file_name
                )
                deleted = True
            except ValueError as ex:
                logger.warning(
                    "Knowledge file '%s' not deleted after promotion: %s",
                    file_name,
                    ex,
                )

        return {
            "profile": profile_name,
            "title": rule_title,
            "path": result["path"],
            "file_deleted": deleted,
        }

    @staticmethod
    def _rule_title_from_file(file_name: str) -> str:
        """
        Derive a readable rule title from a knowledge file name.

        :param file_name: Knowledge file path relative to its folder.
        :return: Title-cased file stem (or a generic title).
        """
        stem = os.path.splitext(os.path.basename(file_name or ""))[0]
        title = re.sub(r"[-_]+", " ", stem).strip()
        return title or "Learned rule"

    # -------------------------------------------------------------------------
    # Profile matching & team helpers
    # -------------------------------------------------------------------------
    def is_profile_match(self, profile: Profile, file_path: str):
        try:
            return profile.file_match and re.search(profile.file_match, file_path)
        except:
            return False

    def get_file_profiles_by_file_path(
        self, file_path: str, profiles: Optional[List[Profile]] = None
    ):
        """
        Return the profiles whose ``file_match`` regex matches *file_path*.

        Args:
            file_path: Absolute or project path used for the match.
            profiles: Optional pre-loaded profile list. Callers matching many
                files pass :meth:`list_all_profiles` once instead of making this
                method re-read the profile chain for every file.

        Returns:
            Matching profiles (linked duplicates reduced).
        """
        candidates = profiles if profiles is not None else self.list_all_profiles()
        file_profiles = [profile for profile in candidates \
          if self.is_profile_match(profile=profile, file_path=file_path)]
        return self.reduce_linked_profiles(profiles=file_profiles)

    def get_profiles_by_name(self, profiles: []):
        return [p for p in self.list_all_profiles() if p.name in profiles]

    def get_profile_content_context(self, profile: Profile):
        return {
          "project_path": lambda: self.settings.abs_project_path,
          "project_name": lambda: self.settings.project_name,
          # "project_tree": lambda: generate_llm_tree(self.settings.abs_project_path)
        }

    def get_profile_With_content(self, profile: Profile):
        """
        Compose a profile for this project: own content + project enrichment.

        Every caller keeps using this method, so no other module needs to know
        that projects can enrich profiles.

        Profile tools are NOT modified here: the agent (SmolAgent) decides which
        profile tools are injected into each request, because it depends on the
        user (who may or may not be allowed to learn) and on the chat turn.

        :param profile: Profile to compose.
        :return: The same profile instance, with the composed content.
        """
        if profile:
            profile.content = self.compose_profile_content(profile)

        context = self.get_profile_content_context(profile=profile)
        
        # Regex explains:
        # {{    -> Matches literal opening braces
        # \s*   -> Matches optional whitespace
        # (\w+) -> Captures the variable name (alphanumeric/underscore)
        # \s*   -> Matches optional whitespace
        # }}    -> Matches literal closing braces
        pattern = r'\{\{\s*(\w+)\s*\}\}'

        def replacement_logic(match):
            variable_name = match.group(1)
            # Returns the value if found, otherwise keeps the original {{var}} text
            fnc = context.get(variable_name, None)
            if fnc:
                return str(fnc())
            return match.group(0)

        profile.parsed_content = re.sub(pattern, replacement_logic, profile.content or "")
        return profile

    def _profiles_by_name_registry(self) -> Dict[str, Profile]:
        """
        Build a ``name -> Profile`` index of every available profile.

        Building the index once avoids repeated (and expensive) full profile
        scans while resolving linked profile names recursively.

        :return: Mapping of profile name to profile entity (with parsed content).
        """
        return {
            profile.name: profile
            for profile in self.list_all_profiles()
            if profile and profile.name
        }

    def _expand_linked_profiles(
        self,
        profiles: List[Profile],
        seen_names: Optional[Set[str]] = None
    ) -> List[Profile]:
        """
        Expand a list of profiles with every profile they link to, recursively.

        Algorithm (one pass per profile, breadth-first):

        1. For each incoming profile we take its **name**.
        2. We find the profile entity for that name (from the registry of all
           available profiles).
        3. We read the entity's ``profiles`` property — a list of linked profile
           **names**.
        4. For every linked name we resolve the profile entity and queue it, so
           the operation repeats until no new profile is found.

        Deduplication is done by profile **name** (never by object equality),
        which makes the resolution deterministic and idempotent, and preserves
        the order in which profiles are discovered.

        :param profiles: Profiles referenced directly by the caller (the chat
                         mentions, file profiles, ...).
        :param seen_names: Optional set of already-resolved profile names,
                           shared across calls to safely ignore circular links.
        :return: The input profiles plus all their (recursively) linked profiles,
                 with no duplicates.
        """
        if seen_names is None:
            seen_names = set()

        # Resolve every linked name against this single snapshot of the
        # available profiles (avoids repeated, inconsistent disk reads).
        registry = self._profiles_by_name_registry()

        resolved: List[Profile] = []
        pending: List[Profile] = [p for p in (profiles or []) if p and p.name]

        while pending:
            profile = pending.pop(0)

            if profile.name in seen_names:
                continue
            seen_names.add(profile.name)

            # Prefer the entity loaded from the registry: it carries the
            # parsed content for use in the system prompt.
            entity = registry.get(profile.name) or profile
            resolved.append(entity)

            # Read the "profiles" property: the list of linked profile names.
            for linked_name in (entity.profiles or []):
                if not linked_name or linked_name in seen_names:
                    continue
                linked_profile = registry.get(linked_name)
                if linked_profile:
                    pending.append(linked_profile)
                else:
                    logger.warning(
                        "Profile '%s' links to unknown profile '%s'",
                        entity.name,
                        linked_name
                    )

        logger.info(
            "Expanded %d profile(s) into %d profile(s) following linked profiles: %s",
            len(profiles or []),
            len(resolved),
            [p.name for p in resolved]
        )
        return resolved

    def get_all_linked_profiles(self, profile: Profile, seen: set = None) -> List[Profile]:
        """
        Return *profile* plus every profile it links to, resolving links
        recursively by profile NAME (see :meth:`_expand_linked_profiles`).

        :param profile: The profile whose links to expand.
        :param seen: Optional set of already-resolved profile names.
        :return: The profile plus all (recursively) linked profiles.
        """
        if not profile or not profile.name:
            return []
        seen_names: Set[str] = set(seen or {})
        return self._expand_linked_profiles(profiles=[profile], seen_names=seen_names)

    def reduce_linked_profiles(self, profiles: List[Profile]) -> List[Profile]:
        """
        Expand a list of profiles with all the profiles they link to,
        recursively, and return them without duplicates.

        For each profile name we find the profile entity, read its ``profiles``
        property (a list of profile names) and, for every linked name, repeat
        the operation until all profiles are loaded.

        :param profiles: Profiles referenced directly by the caller.
        :return: The input profiles plus all their (recursively) linked profiles.
        """
        return self._expand_linked_profiles(profiles=profiles, seen_names=set())

    # -------------------------------------------------------------------------
    # Team (ADDED): profiles the LLM can use in NEW tasks
    # -------------------------------------------------------------------------
    @staticmethod
    def profile_short_description(profile: Profile, max_length: int = 160) -> str:
        """
        Return a short one-line description of *profile* for the team table.

        Resolution order: ``Profile.description`` → first meaningful line of the
        profile content (markdown heading markers removed) → ``Profile.category``.
        Whitespace is collapsed (the description must stay inside a table cell)
        and the result is truncated to *max_length* characters.

        :param profile: The profile to describe.
        :param max_length: Maximum length of the returned description.
        :return: Single-line description (may be an empty string).
        """
        description = (profile.description or "").strip()

        if not description and profile.content:
            for line in profile.content.splitlines():
                candidate = line.strip().lstrip("#").strip()
                if candidate:
                    description = candidate
                    break

        if not description:
            description = profile.category or ""

        # Collapse newlines and repeated spaces so the table stays a table.
        description = " ".join(description.split())

        if len(description) > max_length:
            description = description[:max_length - 3].rstrip() + "..."

        return description

    def get_team_profiles(
        self,
        profiles: List[Profile],
        exclude: Optional[List[Profile]] = None
    ) -> List[Profile]:
        """
        Resolve the TEAM of the given profiles: the profiles the LLM can use in
        NEW tasks.

        A profile declares its team through the ``team`` property — a list of
        profile **names**, like ``profiles`` lists linked profiles. Unlike
        linked profiles:

        * team members are NOT composed into the system prompt; they are only
          offered as a table (name + short description),
        * their links are NOT expanded: a team member's own team is offered only
          once that profile becomes active in a chat.

        Profiles already active in the turn (*exclude*, i.e. the profiles being
        composed) are not offered again, and unknown names are logged and
        skipped. Resolution is best effort: a broken team reference never
        blocks the chat.

        :param profiles: Profiles active in the current turn.
        :param exclude: Profiles (or profile names) that must not be offered.
        :return: Resolved team profiles, deduplicated by name, order preserved.
        """
        if not profiles:
            return []

        registry = self._profiles_by_name_registry()

        excluded_names: Set[str] = set()
        for excluded in (exclude or []):
            if isinstance(excluded, Profile):
                excluded_names.add(excluded.name)
            elif isinstance(excluded, dict):
                excluded_names.add(str(excluded.get("name") or ""))
            else:
                excluded_names.add(str(excluded).lstrip("@"))

        team_profiles: List[Profile] = []
        seen_names: Set[str] = set()

        for profile in profiles:
            for team_name in (profile.team or []):
                # Mentions may declare the member as "@name".
                team_name = (team_name or "").strip().lstrip("@")
                if not team_name or team_name in seen_names \
                        or team_name in excluded_names:
                    continue

                team_profile = registry.get(team_name)
                if not team_profile:
                    logger.warning(
                        "Profile '%s' lists unknown team profile '%s'",
                        profile.name,
                        team_name
                    )
                    continue

                seen_names.add(team_name)
                team_profiles.append(team_profile)

        logger.info(
            "Resolved team of %s: %s",
            [p.name for p in profiles],
            [p.name for p in team_profiles]
        )
        return team_profiles