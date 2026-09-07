import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { getStoredTheme, applyTheme, THEME_STORAGE_KEY } from "../app/theme";

describe("theme persistence SSOT", () => {
  let storage: Record<string, string> = {};
  let attributes: Record<string, string> = {};

  const mockLocalStorage = {
    getItem: vi.fn((key: string) => storage[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      storage[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete storage[key];
    }),
    clear: vi.fn(() => {
      storage = {};
    }),
  };

  const mockDocument = {
    documentElement: {
      getAttribute: vi.fn((name: string) => attributes[name] ?? null),
      setAttribute: vi.fn((name: string, value: string) => {
        attributes[name] = value;
      }),
      removeAttribute: vi.fn((name: string) => {
        delete attributes[name];
      }),
    },
  };

  beforeEach(() => {
    storage = {};
    attributes = {};
    vi.clearAllMocks();
    (globalThis as any).window = { localStorage: mockLocalStorage };
    (globalThis as any).document = mockDocument;
  });

  afterEach(() => {
    delete (globalThis as any).window;
    delete (globalThis as any).document;
  });

  it("reads stored theme from localStorage key fitcv-theme", () => {
    mockLocalStorage.setItem(THEME_STORAGE_KEY, "dark");
    expect(getStoredTheme()).toBe("dark");

    mockLocalStorage.setItem(THEME_STORAGE_KEY, "light");
    expect(getStoredTheme()).toBe("light");
  });

  it("falls back to document attribute when localStorage has no entry", () => {
    mockLocalStorage.clear();
    mockDocument.documentElement.setAttribute("data-theme", "dark");
    expect(getStoredTheme()).toBe("dark");

    mockDocument.documentElement.setAttribute("data-theme", "light");
    expect(getStoredTheme()).toBe("light");
  });

  it("defaults to light when neither localStorage nor document attribute are set", () => {
    expect(getStoredTheme()).toBe("light");
  });

  it("ignores invalid values in localStorage and falls back", () => {
    mockLocalStorage.setItem(THEME_STORAGE_KEY, "invalid-theme");
    expect(getStoredTheme()).toBe("light");
  });

  it("applies theme to document and persists to localStorage across refresh", () => {
    applyTheme("dark");
    expect(mockDocument.documentElement.setAttribute).toHaveBeenCalledWith("data-theme", "dark");
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith(THEME_STORAGE_KEY, "dark");
    expect(storage[THEME_STORAGE_KEY]).toBe("dark");
    expect(attributes["data-theme"]).toBe("dark");

    applyTheme("light");
    expect(mockDocument.documentElement.setAttribute).toHaveBeenCalledWith("data-theme", "light");
    expect(mockLocalStorage.setItem).toHaveBeenCalledWith(THEME_STORAGE_KEY, "light");
    expect(storage[THEME_STORAGE_KEY]).toBe("light");
    expect(attributes["data-theme"]).toBe("light");
  });

  it("handles localStorage throwing without error", () => {
    mockLocalStorage.getItem.mockImplementationOnce(() => {
      throw new Error("Access denied");
    });
    mockLocalStorage.setItem.mockImplementationOnce(() => {
      throw new Error("Access denied");
    });

    expect(() => getStoredTheme()).not.toThrow();
    expect(getStoredTheme()).toBe("light");

    expect(() => applyTheme("dark")).not.toThrow();
    expect(attributes["data-theme"]).toBe("dark");
  });
});
