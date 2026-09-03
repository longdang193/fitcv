import React from "react";
import { ProviderSettingsCore } from "./provider-settings-core";

export const ApiProvidersPage: React.FC = () => <ProviderSettingsCore mode="api-providers" />;

export const route = {
  id: "api-providers",
  path: "#/settings/api-providers",
  title: "API Providers",
  group: "settings" as const,
  order: 35,
  component: ApiProvidersPage,
};

export default route;
