export const DISCORD_ID_PATTERN = /^\d{17,20}$/

export function isValidDiscordId(id: string): boolean {
  return DISCORD_ID_PATTERN.test(id)
}
