import { $storex } from "../store"
import { ChatService } from "./chat"
import { ProjectService } from "./project"

export default {
  $storex,
  chat: new ChatService($storex),
  project: new ProjectService($storex)
}