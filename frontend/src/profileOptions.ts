// Choices offered in onboarding; ids are what the backend stores on the profile
export const CAMPUSES = [
  { id: "atlanta", label: "Atlanta" },
  { id: "alpharetta", label: "Alpharetta" },
  { id: "clarkston", label: "Clarkston" },
  { id: "decatur", label: "Decatur" },
  { id: "dunwoody", label: "Dunwoody" },
  { id: "newton", label: "Newton" },
  { id: "online", label: "Online" },
];

export const PATHWAYS = [
  { id: "business_admin", label: "Business Administration" },
  { id: "nursing", label: "Nursing" },
  { id: "health_sciences", label: "Health Sciences" },
  { id: "psychology", label: "Psychology" },
  { id: "education", label: "Education" },
  { id: "computer_science", label: "Computer Science" },
  { id: "arts", label: "Arts" },
  { id: "undecided", label: "Still deciding" },
];

export const HOLDS = [
  { id: "advisement", label: "Advisement hold" },
  { id: "financial", label: "Financial hold" },
  { id: "registration", label: "Registration hold" },
];

// Each chip adds the KB topic tags it maps to
export const INTERESTS = [
  { label: "Accounting", topics: ["business"] },
  { label: "Startups", topics: ["business", "entrepreneurship"] },
  { label: "AI and tech", topics: ["tech"] },
  { label: "Nursing and health", topics: ["health"] },
  { label: "Psychology", topics: ["psychology"] },
  { label: "Music and art", topics: ["arts"] },
  { label: "Film and media", topics: ["arts"] },
  { label: "Teaching", topics: ["education"] },
  { label: "Careers and internships", topics: ["career"] },
  { label: "Money and support", topics: ["support"] },
];

export const labelFor = (list: { id: string; label: string }[], id: string) => list.find((x) => x.id === id)?.label ?? id;

const ONBOARDED_KEY = "pathfinder.onboarded";

// Per-browser flag; if storage is blocked, onboarding simply shows again
export function isOnboarded(): boolean {
  try {
    return localStorage.getItem(ONBOARDED_KEY) === "1";
  } catch {
    return false;
  }
}

export function markOnboarded(): void {
  try {
    localStorage.setItem(ONBOARDED_KEY, "1");
  } catch {
    // ignore: the profile is still saved server-side
  }
}
