export const CATEGORY_ICONS = {
  Food: "🍔",
  Shopping: "🛍️",
  Transport: "🚌",
  Bills: "🧾",
  Entertainment: "🎬",
  Health: "💊",
  Groceries: "🛒",
  Others: "✨",
};

export function iconFor(category) {
  return CATEGORY_ICONS[category] || "✨";
}
