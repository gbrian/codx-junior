import { $storex } from "../store"
import { ChatService } from "./chat"

export default {
  $storex,
  chat: new ChatService($storex)
}