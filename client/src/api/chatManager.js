class ChatManager {
  constructor() {
    this.localStorageKey = 'chats';
  }

  newChat() {
    const chat = {
      id: new Date().getTime(),
      name: "New chat"
    }
    return chat
  }

  getChats() {
    const chats = localStorage.getItem(this.localStorageKey);
    return chats ? JSON.parse(chats) : [];
  }

  saveChat(chat) {
    const chats = this.getChats();
    if (chats.find(c => c.id === chat.id)) {
      return this.updateChat(chat)
    }
    chats.push(chat);
    localStorage.setItem(this.localStorageKey, JSON.stringify(chats));
  }

  updateChat(updatedChat) {
    let chats = this.getChats();
    chats = chats.map(chat => chat.id === updatedChat.id ? updatedChat : chat);
    localStorage.setItem(this.localStorageKey, JSON.stringify(chats));
  }

  deleteChat({ id: chatId }) {
    let chats = this.getChats();
    chats = chats.filter(chat => chat.id !== chatId);
    localStorage.setItem(this.localStorageKey, JSON.stringify(chats));
  }
}

export default new ChatManager();