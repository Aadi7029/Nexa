// screens/ChatScreen.js
import React, { useCallback, useEffect, useRef, useState } from "react";
import { View, StyleSheet, TouchableOpacity, Alert, Platform, Text } from "react-native";
import { GiftedChat, Bubble, InputToolbar, Send, Message } from "react-native-gifted-chat";
import * as ImagePicker from "expo-image-picker";
import { Ionicons } from "@expo/vector-icons";
import mockServer from "../mock/mockServer";

const DEMO_USER = { _id: 1, name: "You", avatar: "https://i.pravatar.cc/150?img=12" };

export default function ChatScreen({ route }) {
  const conversationId = route.params?.conversationId || "conv-ava";
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    // load initial messages
    (async () => {
      const res = await mockServer.getMessages(conversationId, { limit: 80 });
      if (!mountedRef.current) return;
      setMessages(res.messages || []);
      // mark conversation read when opened (demo: triggers read statuses)
      await mockServer.markConversationRead(conversationId);
    })();

    // subscribe to server events
    const onMsg = ({ conversationId: convId, message }) => {
      if (convId !== conversationId) return;
      setMessages(prev => {
        if (prev.some(m => m._id === message._id)) return prev;
        return GiftedChat.append(prev, [message]);
      });
    };
    const onStatus = ({ conversationId: convId, messageId, status }) => {
      if (convId !== conversationId) return;
      setMessages(prev => prev.map(m => (m._id === messageId ? { ...m, status } : m)));
    };
    const onTyping = ({ conversationId: convId, isTyping }) => {
      if (convId !== conversationId) return;
      setIsTyping(isTyping);
    };

    mockServer.on("message:receive", onMsg);
    mockServer.on("message:status", onStatus);
    mockServer.on("typing", onTyping);

    return () => {
      mountedRef.current = false;
      mockServer.off("message:receive", onMsg);
      mockServer.off("message:status", onStatus);
      mockServer.off("typing", onTyping);
    };
  }, [conversationId]);

  // pick image
  const pickImage = async () => {
    try {
      const { granted } = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!granted) {
        Alert.alert("Permissions required", "Permission to access gallery is required.");
        return;
      }
      const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ImagePicker.MediaTypeOptions.Images, allowsEditing: true, quality: 0.7 });
      if (result.canceled) return;
      const uri = result.assets[0].uri;
      await sendImageMessage(uri);
    } catch (err) { console.warn(err); }
  };

  const takePhoto = async () => {
    try {
      const { granted } = await ImagePicker.requestCameraPermissionsAsync();
      if (!granted) {
        Alert.alert("Permissions required", "Camera permission is required.");
        return;
      }
      const result = await ImagePicker.launchCameraAsync({ allowsEditing: true, quality: 0.7 });
      if (result.canceled) return;
      const uri = result.assets[0].uri;
      await sendImageMessage(uri);
    } catch (err) { console.warn(err); }
  };

  // optimistic image send
  const sendImageMessage = async (uri) => {
    const tempId = `temp-${Math.random().toString(36).slice(2,9)}`;
    const optimistic = { _id: tempId, createdAt: new Date(), user: DEMO_USER, image: uri, status: "sending" };
    setMessages(prev => GiftedChat.append(prev, [optimistic]));

    const uploaded = await mockServer.uploadImageAsync(uri);
    const serverMessage = { _id: Math.random().toString(36).slice(2,9), text: "", createdAt: new Date(), user: DEMO_USER, image: uploaded, status: "sent" };
    await mockServer.sendMessage(conversationId, serverMessage);

    // remove optimistic (server will emit the saved one too, but remove to avoid duplicates)
    setMessages(prev => prev.filter(m => m._id !== tempId));
  };

  // send text optimistic flow
  const onSend = useCallback(async (msgs = []) => {
    if (!msgs || !msgs.length) return;
    const msg = msgs[0];
    const optimistic = { ...msg, _id: `temp-${Math.random().toString(36).slice(2,9)}`, status: "sending" };
    setMessages(prev => GiftedChat.append(prev, [optimistic]));

    const serverMessage = { _id: Math.random().toString(36).slice(2,9), text: msg.text, createdAt: new Date(), user: DEMO_USER, status: "sent" };
    await mockServer.sendMessage(conversationId, serverMessage);

    // remove optimistic local (server emission will add canonical)
    setMessages(prev => prev.filter(m => m._id !== optimistic._id));
  }, [conversationId]);

  // Render bubble (styling)
  const renderBubble = props => (
    <Bubble
      {...props}
      wrapperStyle={{ right: styles.bubbleRight, left: styles.bubbleLeft }}
      textStyle={{ right: styles.textRight, left: styles.textLeft }}
      timeTextStyle={{ right: { color: "#dbeafe" } }}
    />
  );

  // Render each message with ticks for messages sent by YOU
  const renderMessage = props => {
    const { currentMessage } = props;
    return (
      <View>
        <Message {...props} />
        {currentMessage.user && currentMessage.user._id === DEMO_USER._id && (
          <View style={styles.tickRow}>
            {renderTicks(currentMessage.status || "sent")}
          </View>
        )}
      </View>
    );
  };

  // Renders WhatsApp-style ticks for Option A
  const renderTicks = (status) => {
    // statuses: sending, sent, delivered, read
    if (status === "sending") {
      return <Text style={styles.tickText}>• • •</Text>;
    }
    if (status === "sent") {
      return <Text style={styles.tickText}>✓</Text>;
    }
    if (status === "delivered") {
      return <Text style={[styles.tickText, { color: "#6b7280" }]}>✓✓</Text>;
    }
    if (status === "read") {
      return <Text style={[styles.tickText, { color: "#0ea5e9" }]}>✓✓</Text>;
    }
    return null;
  };

  const renderActions = props => (
    <View style={styles.actionsContainer}>
      <TouchableOpacity onPress={pickImage} style={styles.actionBtn} accessibilityLabel="Attach image">
        <Ionicons name="image-outline" size={22} />
      </TouchableOpacity>
      <TouchableOpacity onPress={takePhoto} style={styles.actionBtn} accessibilityLabel="Take photo">
        <Ionicons name="camera-outline" size={22} />
      </TouchableOpacity>
    </View>
  );

  const renderInputToolbar = props => <InputToolbar {...props} containerStyle={styles.inputToolbar} />;

  const renderSend = props => (
    <Send {...props} containerStyle={styles.sendContainer}>
      <View style={styles.sendButton}>
        <Ionicons name="send" size={18} color="#fff" />
      </View>
    </Send>
  );

  return (
    <View style={styles.container}>
      <GiftedChat
        messages={messages}
        onSend={msgs => onSend(msgs)}
        user={DEMO_USER}
        renderBubble={renderBubble}
        renderMessage={renderMessage}
        alwaysShowSend
        isTyping={isTyping}
        placeholder="Type a message..."
        renderInputToolbar={renderInputToolbar}
        renderActions={renderActions}
        renderSend={renderSend}
        showUserAvatar
        scrollToBottom
      />
      {Platform.OS === "android" && <View style={{ height: 8 }} />}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F7F9FC" },
  bubbleRight: { backgroundColor: "#2563EB", padding: 8 },
  bubbleLeft: { backgroundColor: "#F1F5F9", padding: 8 },
  textRight: { color: "#fff", fontSize: 15 },
  textLeft: { color: "#0F172A", fontSize: 15 },
  inputToolbar: { borderTopWidth: 0, marginTop: 6, padding: 6 },
  actionsContainer: { flexDirection: "row", alignItems: "center", marginLeft: 6 },
  actionBtn: {
    width: 40, height: 40, borderRadius: 10, justifyContent: "center", alignItems: "center", marginRight: 8, backgroundColor: "#fff", elevation: 1,
  },
  sendContainer: { justifyContent: "center", marginRight: 8, marginBottom: 4 },
  sendButton: {
    backgroundColor: "#2563EB", borderRadius: 20, padding: 8, width: 40, height: 40, alignItems: "center", justifyContent: "center",
  },
  tickRow: { marginHorizontal: 12, marginTop: 4, alignItems: "flex-end" },
  tickText: { fontSize: 12, color: "#374151" },
});
