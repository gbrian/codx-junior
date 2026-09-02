# Profile Model

The Profile model is a Pydantic BaseModel that defines the structure for user profiles in the CODX system. It contains comprehensive configuration for LLM interactions, API accessibility, and profile organization.

## Core Fields

### Identification & Metadata
- **name** (str): The profile's display name, defaults to empty string
- **path** (str): The file system path where the profile is stored, defaults to empty string
- **category** (str): Classifies the profile type (e.g., "global", "file", "coding"), defaults to empty string
- **tags** (List[str]): Optional list of tags for profile categorization

### Profile Content
- **description** (str): Human-readable description of the profile's purpose, defaults to empty string
- **content** (str, optional): The raw profile content
- **parsed_content** (str, optional): Processed version of the content
- **url** (str): Profile's URL reference, defaults to empty string
- **avatar** (str): Profile avatar/image reference, defaults to empty string

### File Matching
- **file_match** (str): Optional regex pattern to automatically apply profiles based on file absolute paths, defaults to empty string

### Profile Linking
- **profiles** (List[str], optional): List of linked profile names to include with this profile, defaults to empty list

## LLM Configuration

- **llm_model** (str, optional): Specifies which language model to use, defaults to empty string
- **use_knowledge** (bool, optional): Controls whether to leverage knowledge base integration, defaults to True
- **chat_mode** (str, optional): Defines conversation behavior style (e.g., "document writing" or "chat messages")

## User & Access Control

- **user** (CodxUser, optional): Associated user object, defaults to a new CodxUser instance
- **project_id** (str, optional): Identifies the profile's parent project

## Features & Integrations

- **tools** (List[str], optional): List of available tools integrated with this profile, defaults to empty list
- **chat_id** (str, optional): Unique identifier for chat sessions associated with this profile, defaults to empty string

## API Configuration

- **api_settings** (ProfileApiSettings, optional): Controls API accessibility and public metadata

### ProfileApiSettings

Sub-model that manages profile exposure through the API:
- **active** (bool): Determines if the profile is visible through the API, defaults to False
- **model_name** (str, optional): Public-facing name for API exposure
- **description** (str, optional): API-specific description of the profile

## Dependencies
**Imports from:** codx/junior/model/user.py
**Imported by:** codx/junior/model/model.py