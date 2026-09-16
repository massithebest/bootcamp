import { ChatWindow } from "@/components/chat/chat-window";
import {
  AssistantRuntimeProvider,
  AuiConfig,
  Suggestions,
  Tools,
} from "@assistant-ui/react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { productionPlanningToolkit } from "@/components/chat/toolkit";
import { useAgentChat } from "@/hooks/use-agent-chat";
import { EXAMPLE_QUESTIONS, SEED_CONVERSATION } from "@/lib/dummy";

const assistantConfig = AuiConfig({
  tools: Tools({ toolkit: productionPlanningToolkit }),
  suggestions: Suggestions(EXAMPLE_QUESTIONS),
});

export default function App() {
  const chat = useAgentChat(SEED_CONVERSATION);
  return (
    <AssistantRuntimeProvider runtime={chat.runtime} config={assistantConfig}>
      <TooltipProvider>
        <ChatWindow chat={chat} />
      </TooltipProvider>
    </AssistantRuntimeProvider>
  );
}
