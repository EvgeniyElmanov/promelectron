const placeholderColors = [
  '#E3F2FD', '#FCE4EC', '#E8F5E9', '#FFF3E0',
  '#F3E5F5', '#E0F7FA', '#FFF8E1', '#EDE7F6',
];

export function getPlaceholderBg(id) {
  return placeholderColors[Number(id) % placeholderColors.length];
}
