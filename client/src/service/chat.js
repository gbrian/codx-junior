import Service from "./service"

export class ChatService extends Service {
  getUserMessage({ message, files, profiles, images }) {
    return {
      role: 'user',
      content: message,
      images: images.map(JSON.stringify),
      files,
      profiles,
      user: this.$user.username
    }
  }

  async sendMessage({ chat, message }) {
    chat.messages.push(message)
    return this.$storex.projects.chatWihProject(chat)
  }
}
