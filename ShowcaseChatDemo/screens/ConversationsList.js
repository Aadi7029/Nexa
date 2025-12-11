// screens/ConversationsList.js
import React, { useEffect, useState } from "react";
import { View, Text, FlatList, TouchableOpacity, StyleSheet } from "react-native";
import mockServer from "../mock/mockServer";

export default function ConversationsList({ navigation }) {
  const [convs, setConvs] = useState([]);

  const load = async () => {
    const list = await mockServer.getConversations();
    setConvs(list);
  };

  useEffect(() => {
    load();
    // listen for new incoming messages to refresh list preview
    const onMsg = ({ conversationId }) => load();
    mockServer.on("message:receive", onMsg);
    mockServer.on("message:status", onMsg);
    return () => {
      mockServer.off("message:receive", onMsg);
      mockServer.off("message:status", onMsg);
    };
  }, []);

  const renderItem = ({ item }) => (
    <TouchableOpacity style={styles.row} onPress={() => navigation.navigate("Chat", { conversationId: item.id, title: item.title })}>
      <View style={{ flex: 1 }}>
        <Text style={styles.title}>{item.title}</Text>
        <Text style={styles.subtitle} numberOfLines={1}>{item.lastMessage}</Text>
      </View>
      <View style={{ alignItems: "flex-end" }}>
        <Text style={{ color: item.presence?.online ? "#10b981" : "#9CA3AF", fontSize: 12 }}>{item.presence?.online ? "Online" : "Offline"}</Text>
        {item.unread > 0 && (
          <View style={styles.unreadBadge}>
            <Text style={{ color: "#fff", fontSize: 12 }}>{item.unread}</Text>
          </View>
        )}
      </View>
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      <FlatList data={convs} keyExtractor={i => i.id} renderItem={renderItem} ItemSeparatorComponent={() => <View style={{ height: 1, backgroundColor: "#eee" }} />} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#fff" },
  row: { padding: 16, flexDirection: "row", alignItems: "center" },
  title: { fontSize: 16, fontWeight: "700" },
  subtitle: { color: "#6b7280", marginTop: 4 },
  unreadBadge: {
    marginTop: 8,
    backgroundColor: "#2563EB",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },
});
