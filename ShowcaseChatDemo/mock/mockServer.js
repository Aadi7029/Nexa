// mock/mockServer.js
// Demo mock server: messages, statuses and events (EventEmitter)
import { EventEmitter } from "events";

const server = new EventEmitter();

// Demo users
const YOU = { _id: 1, name: "You", avatar: "https://i.pravatar.cc/150?img=12" };
const AVA = { _id: 2, name: "Ava", avatar: "https://i.pravatar.cc/150?img=47" };
const JORDAN = { _id: 3, name: "Jordan", avatar: "https://i.pravatar.cc/150?img=5" };
const BOT = { _id: 4, name: "Support Bot", avatar: "https://i.pravatar.cc/150?img=32" };

// Conversations store (in-memory)
const conversations = {
  "conv-ava": {
    id: "conv-ava",
    title: "Ava (Demo)",
    participants: [YOU, AVA],
    presence: { online: true },
    unread: 0,
    messages: [
      { _id: "a1", text: "Welcome to the demo chat! Tap + to send an image.", createdAt: new Date(Date.now() - 1000 * 60 * 60), user: AVA, status: "read" },
      { _id: "a2", text: "This is a sample older message.", createdAt: new Date(Date.now() - 1000 * 60 * 30), user: AVA, status: "read" },
    ],
  },
  "conv-jordan": {
    id: "conv-jordan",
    title: "Jordan",
    participants: [YOU, JORDAN],
    presence: { online: false },
    unread: 2,
    messages: [
      { _id: "j1", text: "Hey, can you check the docs?", createdAt: new Date(Date.now() - 1000 * 60 * 60 * 5), user: JORDAN, status: "delivered" },
      { _id: "j2", text: "I'll send the link shortly.", createdAt: new Date(Date.now() - 1000 * 60 * 60 * 4), user: YOU, status: "delivered" },
    ],
  },
  "conv-support": {
    id: "conv-support",
    title: "Support Bot",
    participants: [YOU, BOT],
    presence: { online: true },
    unread: 0,
    messages: [
      { _id: "s1", text: "Welcome! Ask me anything about the demo.", createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24), user: BOT, status: "read" },
    ],
  },
};

// helpers
function nowId() { return Math.random().toString(36).slice(2, 9); }
function wait(ms) { return new Promise(res => setTimeout(res, ms)); }

// Emit helpers: message:receive and message:status
async function emitStatusSequence(conversationId, message) {
  // initial saved state = "sent"
  server.emit("message:receive", { conversationId, message });
  // after short delay → delivered
  await wait(700 + Math.random() * 300);
  message.status = "delivered";
  server.emit("message:status", { conversationId, messageId: message._id, status: "delivered" });
  // maybe later mark read
  if (Math.random() > 0.4) {
    await wait(700 + Math.random() * 1000);
    message.status = "read";
    server.emit("message:status", { conversationId, messageId: message._id, status: "read" });
  }
}

// Public API
export default {
  // conversations list
  async getConversations() {
    await wait(180);
    return Object.values(conversations).map(c => ({
      id: c.id,
      title: c.title,
      lastMessage: c.messages[0]?.text || "",
      unread: c.unread || 0,
      presence: c.presence,
    }));
  },

  // get messages (newest-first)
  async getMessages(conversationId, { limit = 40, before } = {}) {
    await wait(180);
    const conv = conversations[conversationId];
    if (!conv) return { messages: [], nextCursor: null };
    let msgs = conv.messages.slice();
    if (before) {
      const idx = msgs.findIndex(m => m._id === before);
      if (idx >= 0) msgs = msgs.slice(idx + 1);
    }
    const slice = msgs.slice(0, limit);
    return { messages: slice, nextCursor: slice.length ? slice[slice.length - 1]._id : null };
  },

  // send message: simulate server save + status progression
  async sendMessage(conversationId, message) {
    const conv = conversations[conversationId];
    if (!conv) throw new Error("Conversation not found");
    // server canonical id & initial status
    const saved = { ...message, _id: message._id || nowId(), status: "sent" };
    conv.messages.unshift(saved);
    // decrement unread for sender? (sender is you) — increment unread for others simulated
    conv.unread = (conv.unread || 0);
    // emit sequences: message:receive + status events
    emitStatusSequence(conversationId, saved);
    // Also, schedule an auto-reply from the remote user for demo realism (not for all convs)
    if (conversationId === "conv-ava" && Math.random() > 0.3) {
      setTimeout(() => {
        const reply = { _id: nowId(), text: "Nice! This is an automated demo reply.", createdAt: new Date(), user: AVA, status: "sent" };
        conv.messages.unshift(reply);
        emitStatusSequence(conversationId, reply);
      }, 900 + Math.random() * 1200);
    } else if (conversationId === "conv-support" && Math.random() > 0.2) {
      setTimeout(() => {
        const reply = { _id: nowId(), text: "Support Bot: Example answer to your message.", createdAt: new Date(), user: BOT, status: "sent" };
        conv.messages.unshift(reply);
        emitStatusSequence(conversationId, reply);
      }, 600 + Math.random() * 1100);
    }
    return saved;
  },

  // simple upload mock — return local uri
  async uploadImageAsync(uri) {
    await wait(230);
    return uri;
  },

  // mark all messages in convo as read (simulate user opened chat)
  async markConversationRead(conversationId) {
    const conv = conversations[conversationId];
    if (!conv) return;
    conv.messages.forEach(m => { if (m.status !== "read") m.status = "read"; });
    conv.unread = 0;
    // emit status update for all messages (for demo simplicity we emit one event per message)
    conv.messages.slice(0, 10).forEach(m => server.emit("message:status", { conversationId, messageId: m._id, status: "read" }));
    server.emit("presence:update", { conversationId, userId: YOU._id, presence: "online" });
  },

  // subscribe/unsubscribe
  on(event, cb) { server.on(event, cb); },
  off(event, cb) { server.off(event, cb); },
};
