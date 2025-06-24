import { $storex } from "../store"
import { ChatService } from "./chat"
import { ProjectService } from "./project"
import { WikiService } from "./wiki"

const services = {
  $storex,
  chat: new ChatService($storex),
  project: new ProjectService($storex),
  wiki: new WikiService($storex),
}
window.$services = services
export default services