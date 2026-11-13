import { goldenBible, caringHands, prayingHands, familyAtSunset, headquartersPhoto } from "./assets.js";

export const groupCovers = { bible: goldenBible, heart: caringHands, prayer: prayingHands, family: familyAtSunset, headquarters: headquartersPhoto };

export function groupCover(group) { return group.cover_url || groupCovers[group.cover] || goldenBible; }
