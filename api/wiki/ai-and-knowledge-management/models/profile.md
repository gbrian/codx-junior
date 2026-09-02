# Profile Model

## Overview

The Profile model is a Pydantic BaseModel that represents a user profile configuration in the Codx system. It contains comprehensive settings for managing profiles including API accessibility, LLM model configuration, and chat-related parameters.

## Fields

### Basic Information
- **name** (str): Profile name. Default: empty string
- **url** (str): Profile URL. Default: empty string
- **avatar** (str): Profile avatar image. Default: empty string
- **description** (str): Profile description. Default: empty string
- **category** (str): Profile category classification (e.g., global, file, coding). Default: empty string
- **path** (str): Profile file path. Default: empty string

### Content
- **content** (Optional[str]): Profile content. Default: None
- **parsed_content** (Optional[str]): Processed/parsed version of the profile content. Default: None

### File Matching
- **file_match** (str): Optional regex pattern to apply profiles based on file absolute path. Default: empty string

### Profile Linking
- **profiles** (Optional[List[str]]): List of linked profiles to include with this profile. Default: empty list

### LLM Configuration
- **llm_model** (Optional[str]): Specifies which LLM model to use. Default: empty string
- **use_knowledge** (Optional[bool]): Enable or disable knowledge base usage. Default: True
- **tools** (Optional[List[str]]): List of available tools for the profile. Default: empty list

### User & Metadata
- **user** (Optional[CodxUser]): Associated CodxUser object. Default: CodxUser instance
- **tags** (Optional[List[str]]): Profile tags for categorization. Default: empty list
- **project_id** (Optional[str]): Associated project identifier. Default: None

### Chat Configuration
- **chat_mode** (Optional[str]): Conversation mode affecting interaction behavior (e.g., document writing or chat messages). Default: None
- **chat_id** (Optional[str]): Unique identifier for chat sessions. Default: empty string

### API Settings
- **api_settings** (Optional[ProfileApiSettings]): Controls profile accessibility through the LLM API. Default: ProfileApiSettings instance

## ProfileApiSettings

Nested model controlling API exposure of the profile.

### Fields
- **active** (bool): Determines if the model is visible through the API. Default: False
- **model_name** (Optional[str]): Custom name for the model in API responses. Default: None
- **description** (Optional[str]): API-specific description of the model. Default: None

## Dependencies
**Imports from:** codx/junior/model/user.py
**Imported by:** codx/junior/model/model.py