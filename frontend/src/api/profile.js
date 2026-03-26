import client from "./client";

export const getProfile = () => client.get("/profile/me");

export const submitOnboarding = (data) => client.post("/profile/onboarding", data);
