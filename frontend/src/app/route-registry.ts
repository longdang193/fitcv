import React from "react";
import overviewRoute from "../features/overview/route";

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

  try {
    // Vite compile-time discovery across feature modules
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
  } catch {
    // Non-Vite or testing environment fallback
  }

  return discovered.sort((a, b) => (a.order ?? 100) - (b.order ?? 100));
}

export function matchRoute(hash: string, routes: FeatureRoute[]): FeatureRoute {
  const normalized = hash ? (hash.startsWith("#") ? hash : `#${hash}`) : "#/overview";
  const found = routes.find((r) => r.path === normalized);
  if (found) {
    return found;
  }
  // Try prefix match for parameterized routes
  const prefixMatch = routes.find(
    (r) => r.path !== "#/overview" && normalized.startsWith(r.path)
  );
  if (prefixMatch) {
    return prefixMatch;
  }
  return routes.find((r) => r.id === "overview") || routes[0];
}
