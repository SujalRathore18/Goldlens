import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api",
  timeout: 15_000,
});

export function runTinyFish(url: string, goal: string) {
  return api.post("/tinyfish/run", { url, goal });
}

export function uploadDataset(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return api.post("/intake/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
}
