import { describe, it, expect } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  DateRangeFilter,
  parseDateRange,
  getClientTimezone,
  getNextDateRangeIndex,
  DATE_RANGES,
  DATE_RANGE_LABELS,
  DEFAULT_DATE_RANGE,
  DateRange,
} from "./DateRangeFilter";

describe("DateRangeFilter and contract helpers", () => {
  describe("parseDateRange", () => {
    it("defaults to today when input is absent, empty, or whitespace", () => {
      expect(parseDateRange(undefined)).toBe("today");
      expect(parseDateRange(null)).toBe("today");
      expect(parseDateRange("")).toBe("today");
      expect(parseDateRange("   ")).toBe("today");
    });

    it("defaults to today for invalid values", () => {
      expect(parseDateRange("yesterday")).toBe("today");
      expect(parseDateRange("1y")).toBe("today");
      expect(parseDateRange("invalid")).toBe("today");
      expect(parseDateRange("today_and_more")).toBe("today");
    });

    it("parses valid date range values case-insensitively with whitespace trimmed", () => {
      expect(parseDateRange("today")).toBe("today");
      expect(parseDateRange("24h")).toBe("24h");
      expect(parseDateRange("7d")).toBe("7d");
      expect(parseDateRange("30d")).toBe("30d");
      expect(parseDateRange("all")).toBe("all");
      expect(parseDateRange(" TODAY ")).toBe("today");
      expect(parseDateRange("24H")).toBe("24h");
      expect(parseDateRange("7D")).toBe("7d");
      expect(parseDateRange("30D")).toBe("30d");
      expect(parseDateRange("ALL")).toBe("all");
    });
  });

  describe("DATE_RANGE_LABELS and definitions", () => {
    it("defines 5 canonical ranges matching plan specification", () => {
      expect(DATE_RANGES).toEqual(["today", "24h", "7d", "30d", "all"]);
      expect(DEFAULT_DATE_RANGE).toBe("today");
    });

    it("provides exact expected labels: Today | 24h | 7D | 30D | All", () => {
      expect(DATE_RANGE_LABELS.today).toBe("Today");
      expect(DATE_RANGE_LABELS["24h"]).toBe("24h");
      expect(DATE_RANGE_LABELS["7d"]).toBe("7D");
      expect(DATE_RANGE_LABELS["30d"]).toBe("30D");
      expect(DATE_RANGE_LABELS.all).toBe("All");
    });
  });

  describe("getClientTimezone", () => {
    it("returns resolved IANA timezone or undefined on error", () => {
      const tz = getClientTimezone();
      expect(typeof tz === "string" || tz === undefined).toBe(true);
      if (typeof tz === "string") {
        expect(tz.length).toBeGreaterThan(0);
      }
    });
  });

  describe("getNextDateRangeIndex", () => {
    it("advances index on ArrowRight and ArrowDown, wrapping around at end", () => {
      expect(getNextDateRangeIndex("ArrowRight", 0, 5)).toBe(1);
      expect(getNextDateRangeIndex("ArrowRight", 3, 5)).toBe(4);
      expect(getNextDateRangeIndex("ArrowRight", 4, 5)).toBe(0);
      expect(getNextDateRangeIndex("ArrowDown", 2, 5)).toBe(3);
      expect(getNextDateRangeIndex("ArrowDown", 4, 5)).toBe(0);
    });

    it("retreats index on ArrowLeft and ArrowUp, wrapping around at start", () => {
      expect(getNextDateRangeIndex("ArrowLeft", 2, 5)).toBe(1);
      expect(getNextDateRangeIndex("ArrowLeft", 0, 5)).toBe(4);
      expect(getNextDateRangeIndex("ArrowUp", 1, 5)).toBe(0);
      expect(getNextDateRangeIndex("ArrowUp", 0, 5)).toBe(4);
    });

    it("jumps to first index on Home and last index on End", () => {
      expect(getNextDateRangeIndex("Home", 3, 5)).toBe(0);
      expect(getNextDateRangeIndex("Home", 0, 5)).toBe(0);
      expect(getNextDateRangeIndex("End", 1, 5)).toBe(4);
      expect(getNextDateRangeIndex("End", 4, 5)).toBe(4);
    });

    it("returns null for unrelated keys or empty list", () => {
      expect(getNextDateRangeIndex("Tab", 0, 5)).toBeNull();
      expect(getNextDateRangeIndex("Enter", 0, 5)).toBeNull();
      expect(getNextDateRangeIndex("ArrowRight", 0, 0)).toBeNull();
    });
  });

  describe("DateRangeFilter component markup and accessibility", () => {
    it("renders accessible segmented control radiogroup with 5 buttons", () => {
      const markup = renderToStaticMarkup(
        React.createElement(DateRangeFilter, {
          value: "today",
          onChange: () => {},
        })
      );

      expect(markup).toContain("role=\"radiogroup\"");
      expect(markup).toContain("aria-label=\"Filter by date range\"");
      expect(markup).toContain("Today");
      expect(markup).toContain("24h");
      expect(markup).toContain("7D");
      expect(markup).toContain("30D");
      expect(markup).toContain("All");
      expect(markup).toContain("data-date-range=\"today\"");
      expect(markup).toContain("data-date-range=\"24h\"");
      expect(markup).toContain("data-date-range=\"7d\"");
      expect(markup).toContain("data-date-range=\"30d\"");
      expect(markup).toContain("data-date-range=\"all\"");
    });

    it("sets aria-checked and tabIndex according to active selection", () => {
      const markup7d = renderToStaticMarkup(
        React.createElement(DateRangeFilter, {
          value: "7d",
          onChange: () => {},
        })
      );

      const btn7d = markup7d.match(/<button[^>]*data-date-range="7d"[^>]*>/)?.[0] || "";
      expect(btn7d).toContain('aria-checked="true"');
      expect(btn7d).toContain('tabindex="0"');

      const btnToday = markup7d.match(/<button[^>]*data-date-range="today"[^>]*>/)?.[0] || "";
      expect(btnToday).toContain('aria-checked="false"');
      expect(btnToday).toContain('tabindex="-1"');

      const btnAll = markup7d.match(/<button[^>]*data-date-range="all"[^>]*>/)?.[0] || "";
      expect(btnAll).toContain('aria-checked="false"');
      expect(btnAll).toContain('tabindex="-1"');
    });

    it("falls back safely to today if invalid value is passed as prop", () => {
      const markup = renderToStaticMarkup(
        React.createElement(DateRangeFilter, {
          value: "not-a-range" as DateRange,
          onChange: () => {},
        })
      );

      const btn = markup.match(/<button[^>]*data-date-range="today"[^>]*>/)?.[0] || "";
      expect(btn).toContain('aria-checked="true"');
      expect(btn).toContain('tabindex="0"');
    });

    it("disables all radio buttons when disabled prop is true", () => {
      const markup = renderToStaticMarkup(
        React.createElement(DateRangeFilter, {
          value: "today",
          onChange: () => {},
          disabled: true,
        })
      );

      const disabledMatches = markup.match(/disabled=""/g);
      expect(disabledMatches?.length).toBe(5);
    });
  });
});