import os

CODING_PROFILES = [
    {
        "type": "vue coding profile",
        "match": lambda file_path: True if file_path.endswith("\\.vue") else False,
        "file": "vue.md"
    }
]
    
BASE_DIR=os.path.basename(__file__)

def get_coding_profiles(file_paths: [str]):
    def read_profile(profile):
        with open(f"{BASE_DIR}/{profile['file']}") as f:
            profile["content"] = f.read()
        return profile

    def is_match(profile):
        for file_path in file_paths:
            if profile["match"](file_path):
                return True
        return False

    return [read_profile(v) for v in CODING_PROFILES if is_match(v)]
