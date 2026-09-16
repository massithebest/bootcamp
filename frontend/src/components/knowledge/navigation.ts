import { createContext, useContext } from "react";
import type { KnowledgeTarget } from "@/types/knowledge";

export const KnowledgeNavigation = createContext<(target?: KnowledgeTarget) => void>(() => {});
export const useKnowledgeNavigation = () => useContext(KnowledgeNavigation);
