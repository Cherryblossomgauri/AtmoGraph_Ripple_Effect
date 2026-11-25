
import axios from "axios";

const API_BASE_URL =
  "https://atmograph-ripple-effect.onrender.com";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
  headers: {
    "Content-Type": "application/json"
  }
});

export const getGraphData = async () => {
  const response = await api.get("/graph");

  return response.data;
};

export default api;
