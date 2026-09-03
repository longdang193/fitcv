import React from "react";
import { ProviderSettingsCore } from "../api-providers/provider-settings-core";

export const LlmConfigurationPage: React.FC = () => <ProviderSettingsCore mode="llm-configuration" />;

export const route = {
  id: "llm-configuration",
  path: "#/settings/llm-configuration",
  title: "LLM Configuration",
  group: "settings" as const,
  order: 36,
  component: LlmConfigurationPage,
};

export default route;
