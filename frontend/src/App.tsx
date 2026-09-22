import { ChatWindow } from "@/components/chat/chat-window";
import {
  AssistantRuntimeProvider,
  AuiConfig,
  Suggestions,
  Tools,
} from "@assistant-ui/react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { productionPlanningToolkit } from "@/components/chat/toolkit";
import { useAgentRuntime } from "@/hooks/use-agent-runtime";
import { EXAMPLE_QUESTIONS } from "@/lib/dummy";

const assistantConfig = AuiConfig({
  tools: Tools({ toolkit: productionPlanningToolkit }),
  suggestions: Suggestions(EXAMPLE_QUESTIONS),
});

export default function App() {
  const runtime = useAgentRuntime();
  return (
    <AssistantRuntimeProvider runtime={runtime} config={assistantConfig}>
      <TooltipProvider>
        <ChatWindow />
      </TooltipProvider>
    </AssistantRuntimeProvider>
  );
}
