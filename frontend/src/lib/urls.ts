export function getSafeAdminUrl(value: string): string | null {
  try {
    const url = new URL(value);
    const isHttp = url.protocol === "http:" || url.protocol === "https:";

    if (!isHttp || !url.hostname || url.username || url.password) {
      return null;
    }

    return url.toString();
  } catch {
    return null;
  }
}
