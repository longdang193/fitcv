import React from "react";
import overviewRoute from "./overview-route";

export type RouteGroup = "workspace" | "settings" | "system";

export interface FeatureRoute {
  id: string;
  path: string; // e.g. "#/overview", "#/candidate-profile"
  title: string;
  group: RouteGroup;
  icon?: React.ReactNode;
  order?: number;
  component: React.ComponentType;
}

export interface RouteModule {
  route?: FeatureRoute;
  default?: FeatureRoute | React.ComponentType;
}

const fallbackRoutes: FeatureRoute[] = [overviewRoute];

export function discoverFeatureRoutes(): FeatureRoute[] {
  const discovered: FeatureRoute[] = [...fallbackRoutes];
  const knownIds = new Set(discovered.map((r) => r.id));

  const modules: Record<string, unknown> = import.meta.glob("../features/**/route.tsx", {
    eager: true,
  });

  for (const [, untypedMod] of Object.entries(modules)) {
    const mod = untypedMod as RouteModule;
    let routeObj: FeatureRoute | undefined;

    if (mod.route && typeof mod.route === "object" && mod.route.id) {
      routeObj = mod.route;
    } else if (
      mod.default &&
      typeof mod.default === "object" &&
      "id" in mod.default &&
      (mod.default as FeatureRoute).id
    ) {
      routeObj = mod.default as FeatureRoute;
    }

    if (routeObj) {
      if (knownIds.has(routeObj.id)) {
        const idx = discovered.findIndex((r) => r.id === routeObj!.id);
        discovered[idx] = routeObj;
      } else {
        discovered.push(routeObj);
        knownIds.add(routeObj.id);
      }
    }
  }

  return discovered.sort((a, b) => (a.order ?? 100) - (b.order ?? 100));
}

export function matchRoute(hash: string, routes: FeatureRoute[]): FeatureRoute {
  const normalized = hash ? (hash.startsWith("#") ? hash : `#${hash}`) : "#/overview";
  const pathOnly = normalized.split("?")[0];

  // 1. Exact match with pathOnly or full normalized
  const exact = routes.find((r) => r.path === pathOnly || r.path === normalized);
  if (exact) {
    return exact;
  }

  // 2. Alias normalizations, including nested deep links.
  const aliases: Record<string, string> = {
    "#/settings/api-providers": "api-providers",
    "#/api-providers": "api-providers",
    "#/settings/providers": "api-providers",
    "#/providers": "api-providers",
    "#/settings/llm-configuration": "llm-configuration",
    "#/llm-configuration": "llm-configuration",
    "#/settings/synonyms": "synonyms",
    "#/synonyms": "synonyms",
    "#/candidate-profiles": "candidate-profile",
    "#/candidate-profile": "candidate-profile",
    "#/settings/pipeline": "pipeline-settings",
    "#/pipeline-settings": "pipeline-settings",
    "#/preference-optimization": "preference-optimization",
    "#preference-optimization": "preference-optimization",
    "#/settings/preference-optimization": "preference-optimization",
    "#/settings/personalization": "preference-optimization",
    "#personalization": "preference-optimization",
    "#/personalization": "preference-optimization",
  };
  const alias = Object.entries(aliases).find(
    ([prefix]) => pathOnly === prefix || pathOnly.startsWith(`${prefix}/`)
  );
  if (alias) {
    const aliasRoute = routes.find((r) => r.id === alias[1]);
    if (aliasRoute) return aliasRoute;
  }

  // 3. Prefix match for parameterized/sub-paths (e.g. #/candidate-profile/create)
  const prefixMatch = routes.find(
    (r) =>
      r.path !== "#/overview" &&
      (pathOnly.startsWith(r.path + "/") || pathOnly.startsWith(r.path + "?"))
  );
  if (prefixMatch) {
    return prefixMatch;
  }

  return routes.find((r) => r.id === "overview") || routes[0];
}
