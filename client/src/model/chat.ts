export interface Message {
  doc_id?: string
  role: string
  task_item: string
  content: string
  think?: string
  hide: boolean
  is_answer: boolean
  improvement: boolean
  created_at: string
  updated_at: string
  images: string[]
  files: string[]
  meta_data?: Record<string, any>
  profiles: string[]
  user?: string
  knowledge_topics: string[]
  done?: boolean
  is_thinking?: boolean
  disable_knowledge?: boolean
  read_by: string[]
  error?: string
}

export interface ChatId {
  chat_id: string
  project_id: string
}

export interface KanbanColumn {
  id: string
  name: string
}

export interface Chat {
  id?: string
  doc_id?: string
  project_id?: string
  owner_project_id?: string
  parent_id?: string
  parent_owner_project_id?: string
  parent_project_id?: string
  child_index?: number
  message_id?: string
  status: string
  file_list: string[]
  check_lists?: Record<string, any>[]
  profiles: string[]
  users: string[]
  name: string
  pinned?: boolean
  description: string
  messages: Message[]
  created_at: string
  updated_at: string
  mode: string
  kanban_id: string
  column_id: string
  board: string
  column: string
  columns: KanbanColumn[]
  chat_index?: number
  url: string
  branch: string
  file_path: string
  llm_model?: string
  visibility?: string
  remote_url?: string
  knowledge_topics: string[]
  chat_links: ChatId[]
  pr_view?: Record<string, any>
  temp?: boolean
}

export interface MessageMention {
  mention?: string
  name: string
  file?: string
  profile?: { name: string }
  active?: boolean
}

export interface SubTaskPayload {
  name: string
  messages: Message[]
  project_id: string
  parent_id: string
  file_list: string[]
  profiles: string[]
  mode: string
  column: string
  board: string
  metadata: Record<string, any>
  activateChat: boolean
}