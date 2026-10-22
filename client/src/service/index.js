import { $storex } from "../store"
import { ChatService } from "./chat"
import { ProjectService } from "./project"
import { WikiService } from "./wiki"
import { PrAnalysisService } from "./prAnalysis"

const services = {
  $storex,
  chat: new ChatService($storex),
  project: new ProjectService($storex),
  wiki: new WikiService($storex),
  prAnalysis: new PrAnalysisService($storex),
}
window.$services = services
export default services