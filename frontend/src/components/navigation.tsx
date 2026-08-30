import React from "react";

export interface NavItem {
  id: string;
  label: string;
  href: string;
  icon?: React.ReactNode;
  count?: number;
  active?: boolean;
}

export interface NavGroup {
  id: string;
  title: string;
  items: NavItem[];
  defaultOpen?: boolean;
}

export interface NavigationProps {
  groups: NavGroup[];
  currentPath: string;
  onNavigate?: (href: string) => void;
}

export const Navigation: React.FC<NavigationProps> = ({
  groups,
  currentPath,
  onNavigate,
}) => {
  const handleClick = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    if (onNavigate) {
      e.preventDefault();
      onNavigate(href);
    }
  };

  return (
    <nav className="nav-container" aria-label="Main Navigation">
      {groups.map((group) => (
        <details key={group.id} className="nav-group" open={group.defaultOpen ?? true}>
          <summary>{group.title}</summary>
          <div className="nav-children">
            {group.items.map((item) => {
              const isActive =
                item.active ??
                (currentPath === item.href ||
                  (item.href !== "#/overview" && currentPath.startsWith(item.href)));
              return (
                <a
                  key={item.id}
                  href={item.href}
                  className={`nav-link ${isActive ? "active" : ""}`.trim()}
                  aria-current={isActive ? "page" : undefined}
                  onClick={(e) => handleClick(e, item.href)}
                >
                  {item.icon && <span className="nav-icon">{item.icon}</span>}
                  <span style={{ flex: 1 }}>{item.label}</span>
                  {typeof item.count === "number" && (
                    <span
                      className="badge"
                      style={{ fontSize: 11, minHeight: 20, padding: "0 6px" }}
                    >
                      {item.count}
                    </span>
                  )}
                </a>
              );
            })}
          </div>
        </details>
      ))}
    </nav>
  );
};
