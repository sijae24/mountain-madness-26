const ELABELS = {
  joy: "Joy",
  sadness: "Sadness",
  anger: "Anger",
  fear: "Fear",
  disgust: "Disgust",
  surprise: "Surprise",
  neutral: "Neutral",
};

const PLAY = "M8 5v14l11-7z";
const PAUSE = "M6 19h4V5H6zm8-14v14h4V5z";
const HEART_OUTLINE =
  "M16.5 3c-1.74 0-3.41.81-4.5 2.09C10.91 3.81 9.24 3 7.5 3 4.42 3 2 5.42 2 8.5c0 3.78 3.4 6.86 8.55 11.54L12 21.35l1.45-1.32C18.6 15.36 22 12.28 22 8.5 22 5.42 19.58 3 16.5 3zm-4.4 15.55l-.1.1-.1-.1C7.14 14.24 4 11.39 4 8.5 4 6.5 5.5 5 7.5 5c1.54 0 3.04.99 3.57 2.36h1.87C13.46 5.99 14.96 5 16.5 5c2 0 3.5 1.5 3.5 3.5 0 2.89-3.14 5.74-7.9 10.05z";
const HEART_FILLED =
  "M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z";
const PLUS_ICON = "M19 13H13V19H11V13H5V11H11V5H13V11H19V13Z";
const DEFAULT_ART =
  '<svg viewBox="0 0 24 24"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg>';

const mainEl = document.getElementById("mainEl");
const topbar = document.getElementById("topbar");
const navLinks = Array.from(document.querySelectorAll(".nav-link[data-view]"));

const hero = document.getElementById("hero");
const composer = document.getElementById("composer");
const form = document.getElementById("mood-form");
const moodInput = document.getElementById("mood-input");
const submitBtn = document.getElementById("submit-btn");

const globalSearchInput = document.getElementById("global-search-input");
const listFilterInput = document.getElementById("list-filter");
const exportSpotifyBtn = document.getElementById("export-spotify-btn");
const clearRecentBtn = document.getElementById("clear-recent-btn");
const resultsActions = document.querySelector(".results-actions");

const loader = document.getElementById("loader");
const results = document.getElementById("results");
const resTitle = document.getElementById("res-title");
const tracksList = document.getElementById("tracks-list");
const errMsg = document.getElementById("err-msg");
const emotionRow = document.getElementById("emotion-row");
const eDot = document.getElementById("e-dot");
const eTextVal = document.getElementById("e-text-val");

const likedCount = document.getElementById("liked-count");
const playlistList = document.getElementById("playlist-list");
const newPlaylistBtn = document.getElementById("new-playlist-btn");
const userAvatar = document.getElementById("user-avatar");
const userLabel = document.getElementById("user-label");
const authBtn = document.getElementById("auth-btn");

const barArt = document.getElementById("bar-art");
const barName = document.getElementById("bar-name");
const barArtist = document.getElementById("bar-artist");
const barHeartBtn = document.getElementById("bar-heart-btn");
const barHeartPath = barHeartBtn.querySelector("path");
const barPlayBtn = document.getElementById("bar-play-btn");
const barPrevBtn = document.getElementById("bar-prev-btn");
const barNextBtn = document.getElementById("bar-next-btn");
const barIconPath = document.getElementById("bar-icon").querySelector("path");
const barTrack = document.getElementById("bar-track");
const barFill = document.getElementById("bar-fill");
const barThumb = document.getElementById("bar-thumb");
const barCur = document.getElementById("bar-cur");
const barDur = document.getElementById("bar-dur");
const barVol = document.querySelector(".bar-vol");
const barVolFill = document.querySelector(".bar-vol-fill");

const state = {
  currentView: "home",
  previousViewBeforeSearch: "home",
  currentPlaylistId: null,
  homeTitle: "Your <em>mood</em> playlist",
  hasHomeResults: false,
  filterQuery: "",
  homeTracks: [],
  likedTracks: [],
  recentTracks: [],
  playlists: [],
  playlistTracks: [],
  searchTracks: [],
  currentTracks: [],
  renderedTracks: [],
  searchDebounce: null,
};

let audio = null;
let activeTrack = null;
let activeRow = null;
let activePlayBtn = null;
let ticker = null;
let currentVolume = 0.68;
let isDraggingVolume = false;
let supabaseClient = null;
let supabaseEnabled = false;
let authUser = null;
let authAccessToken = null;

const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
const esc = (s) =>
  String(s || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;");
const setD = (el, d) => el && el.setAttribute("d", d);
const trackKey = (track) => `${track?.name || ""}::${track?.artist || ""}`.toLowerCase();
const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

function normalizeTrack(track) {
  return {
    name: track?.name || "Unknown Title",
    artist: track?.artist || "Unknown Artist",
    preview_url: track?.preview_url || null,
    album_cover: track?.album_cover || null,
    lastfm_url: track?.lastfm_url || track?.spotify_url || null,
    spotify_url: track?.spotify_url || track?.lastfm_url || null,
  };
}

function likedSet() {
  return new Set(state.likedTracks.map(trackKey));
}

function isLiked(track) {
  return likedSet().has(trackKey(track));
}

function showError(message) {
  errMsg.textContent = message;
  errMsg.classList.add("on");
}

function clearError() {
  errMsg.textContent = "";
  errMsg.classList.remove("on");
}

function setLoading(on) {
  loader.classList.toggle("on", !!on);
}

function setComposerVisible(visible) {
  hero.style.display = visible ? "" : "none";
  composer.style.display = visible ? "" : "none";
}

function initials(value) {
  const text = String(value || "").trim();
  if (!text) return "MW";
  const parts = text.split(/[\s@._-]+/).filter(Boolean);
  if (!parts.length) return "MW";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0] || ""}${parts[1][0] || ""}`.toUpperCase();
}

function updateAuthUI() {
  if (!authBtn || !userLabel || !userAvatar) return;

  if (!supabaseEnabled) {
    userLabel.textContent = "Local";
    userAvatar.textContent = "MW";
    authBtn.style.display = "none";
    return;
  }

  if (authUser?.email) {
    userLabel.textContent = authUser.email;
    userAvatar.textContent = initials(authUser.email);
    authBtn.textContent = "Sign Out";
    authBtn.style.display = "inline-flex";
    return;
  }

  userLabel.textContent = "Guest";
  userAvatar.textContent = "MW";
  authBtn.textContent = "Sign In";
  authBtn.style.display = "inline-flex";
}

async function syncServerAuthSession(token) {
  if (!supabaseEnabled || !token) return;
  await fetch("/api/auth/session", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
}

async function clearServerAuthSession() {
  if (!supabaseEnabled) return;
  await fetch("/api/auth/session", { method: "DELETE" });
}

async function getAccessToken() {
  if (!supabaseClient) return null;
  const { data } = await supabaseClient.auth.getSession();
  authAccessToken = data?.session?.access_token || null;
  return authAccessToken;
}

async function refreshAuthState() {
  if (!supabaseClient) {
    authUser = null;
    authAccessToken = null;
    updateAuthUI();
    return;
  }

  const { data } = await supabaseClient.auth.getSession();
  authUser = data?.session?.user || null;
  authAccessToken = data?.session?.access_token || null;

  if (authAccessToken) {
    await syncServerAuthSession(authAccessToken);
  } else {
    await clearServerAuthSession();
  }
  updateAuthUI();
}

async function initSupabaseAuth() {
  const cfg = await fetch("/api/config").then((r) => r.json()).catch(() => ({}));
  supabaseEnabled = !!cfg.supabase_enabled;

  if (cfg.storage_mode === "supabase" && !supabaseEnabled) {
    showError("Supabase mode is enabled but client config is missing. Add SUPABASE_URL and SUPABASE_ANON_KEY.");
    updateAuthUI();
    return;
  }

  if (!supabaseEnabled) {
    updateAuthUI();
    return;
  }

  if (!window.supabase?.createClient) {
    showError("Supabase client failed to load.");
    updateAuthUI();
    return;
  }

  supabaseClient = window.supabase.createClient(cfg.supabase_url, cfg.supabase_anon_key);
  await refreshAuthState();

  supabaseClient.auth.onAuthStateChange(async (_event, sessionData) => {
    authUser = sessionData?.user || null;
    authAccessToken = sessionData?.access_token || null;
    if (authAccessToken) {
      await syncServerAuthSession(authAccessToken);
    } else {
      await clearServerAuthSession();
    }
    updateAuthUI();
  });
}

async function startAuthFlow() {
  if (!supabaseEnabled || !supabaseClient) {
    return;
  }

  if (authUser) {
    await supabaseClient.auth.signOut();
    authUser = null;
    authAccessToken = null;
    state.likedTracks = [];
    state.recentTracks = [];
    state.playlists = [];
    state.playlistTracks = [];
    state.currentPlaylistId = null;
    updateLikedCount();
    renderPlaylistsSidebar();
    renderCurrentView();
    updateAuthUI();
    return;
  }

  const mode = (window.prompt("Type login or signup:", "login") || "").trim().toLowerCase();
  if (!mode) return;

  const email = (window.prompt("Email:") || "").trim();
  if (!email) return;
  const password = window.prompt("Password (min 6 chars):") || "";
  if (!password) return;

  try {
    if (mode === "signup" || mode === "sign-up" || mode === "register") {
      const { error } = await supabaseClient.auth.signUp({ email, password });
      if (error) throw error;
      window.alert("Account created. If email confirmation is enabled, confirm it then sign in.");
    } else {
      const { error } = await supabaseClient.auth.signInWithPassword({ email, password });
      if (error) throw error;
      await refreshLikedTracks();
      await refreshRecentTracks();
      await refreshPlaylists();
      renderCurrentView();
    }
  } catch (error) {
    showError(error.message || "Auth failed.");
    window.alert(`Auth failed: ${error.message || "unknown error"}`);
  }
}

async function api(url, options = {}) {
  const token = await getAccessToken();
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.error || `Request failed (${response.status})`);
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return data;
}

function updateLikedCount() {
  likedCount.textContent = String(state.likedTracks.length);
}

function setBarArt(track) {
  if (track?.album_cover) {
    barArt.innerHTML = `<img src="${esc(track.album_cover)}" alt="${esc(track.name)} cover">`;
    return;
  }
  barArt.innerHTML = DEFAULT_ART;
}

function setBarHeartState(track) {
  const liked = !!track && isLiked(track);
  barHeartBtn.classList.toggle("active", liked);
  barHeartBtn.disabled = !track;
  setD(barHeartPath, liked ? HEART_FILLED : HEART_OUTLINE);
}

function setTrackLikeState(button, track) {
  const liked = isLiked(track);
  button.classList.toggle("active-btn", liked);
  setD(button.querySelector("path"), liked ? HEART_FILLED : HEART_OUTLINE);
}

function setTrackPlayState(button, playing) {
  if (!button) return;
  const path = button.querySelector("path");
  const label = button.querySelector("span");

  if (button.disabled) {
    button.classList.remove("active-btn");
    setD(path, PLAY);
    if (label) label.textContent = "No Preview";
    return;
  }

  if (playing) {
    button.classList.add("active-btn");
    setD(path, PAUSE);
    if (label) label.textContent = "Pause";
  } else {
    button.classList.remove("active-btn");
    setD(path, PLAY);
    if (label) label.textContent = "Play";
  }
}

function setIdle() {
  barName.textContent = "Not playing";
  barName.classList.add("idle");
  barArtist.textContent = "";
  barCur.textContent = "0:00";
  barDur.textContent = "0:30";
  barFill.style.width = "0%";
  barThumb.style.left = "0%";
  setBarArt(null);
  setBarHeartState(null);
  setD(barIconPath, PLAY);
}

function updateVolumeUI() {
  if (!barVolFill) return;
  barVolFill.style.width = `${Math.round(currentVolume * 100)}%`;
}

function setVolume(value) {
  currentVolume = clamp(value, 0, 1);
  if (audio) {
    audio.volume = currentVolume;
  }
  updateVolumeUI();
}

function updateVolumeFromPointer(clientX) {
  if (!barVol) return;
  const rect = barVol.getBoundingClientRect();
  const raw = (clientX - rect.left) / rect.width;
  setVolume(raw);
}

function stopAll() {
  if (audio) {
    audio.pause();
    audio.currentTime = 0;
  }
  if (activePlayBtn) {
    setTrackPlayState(activePlayBtn, false);
  }
  if (activeRow) {
    activeRow.classList.remove("active");
  }
  clearInterval(ticker);

  audio = null;
  activeTrack = null;
  activeRow = null;
  activePlayBtn = null;
  setD(barIconPath, PLAY);
  setBarHeartState(null);
  barFill.style.width = "0%";
  barThumb.style.left = "0%";
  barCur.textContent = "0:00";
}

function syncProgress() {
  if (!audio?.duration || !Number.isFinite(audio.duration)) return;
  const progress = audio.currentTime / audio.duration;
  barFill.style.width = `${progress * 100}%`;
  barThumb.style.left = `${progress * 100}%`;
  barCur.textContent = fmt(audio.currentTime);
}

function getRenderedRow(track) {
  const key = trackKey(track);
  return Array.from(tracksList.querySelectorAll(".track")).find((row) => row.dataset.key === key) || null;
}

async function recordRecent(track) {
  try {
    await api("/api/recent", {
      method: "POST",
      body: JSON.stringify({ track }),
    });

    const key = trackKey(track);
    state.recentTracks = [normalizeTrack(track), ...state.recentTracks.filter((t) => trackKey(t) !== key)].slice(0, 10);
    if (state.currentView === "recent") {
      renderCurrentView();
    }
  } catch (_err) {
    // Non-blocking for playback.
  }
}

function getPlaybackQueue() {
  return state.renderedTracks.length ? state.renderedTracks : state.currentTracks;
}

function playAdjacent(step) {
  const queue = getPlaybackQueue();
  if (!queue.length) return;

  let start = activeTrack ? queue.findIndex((t) => trackKey(t) === trackKey(activeTrack)) : -1;
  if (start < 0) start = step > 0 ? -1 : 0;

  for (let i = 1; i <= queue.length; i += 1) {
    const idx = (start + step * i + queue.length) % queue.length;
    const candidate = queue[idx];
    if (candidate.preview_url) {
      playTrack(candidate);
      return;
    }
  }
}

function toggleCurrentPlay() {
  if (!audio) return;
  if (audio.paused) {
    audio.play();
    setD(barIconPath, PAUSE);
    setTrackPlayState(activePlayBtn, true);
  } else {
    audio.pause();
    setD(barIconPath, PLAY);
    setTrackPlayState(activePlayBtn, false);
  }
}

function playTrack(track, row = null, btn = null) {
  const normalized = normalizeTrack(track);
  if (!normalized.preview_url) return;

  if (activeTrack && trackKey(activeTrack) === trackKey(normalized) && audio) {
    toggleCurrentPlay();
    return;
  }

  stopAll();
  audio = new Audio(normalized.preview_url);
  audio.volume = currentVolume;
  activeTrack = normalized;

  activeRow = row || getRenderedRow(normalized);
  activePlayBtn = btn || activeRow?.querySelector(".prev-btn") || null;

  if (activeRow) activeRow.classList.add("active");
  if (activePlayBtn) {
    setTrackPlayState(activePlayBtn, true);
  }

  setD(barIconPath, PAUSE);
  barName.textContent = normalized.name;
  barName.classList.remove("idle");
  barArtist.textContent = normalized.artist;
  setBarArt(normalized);
  setBarHeartState(normalized);

  audio.addEventListener("loadedmetadata", () => {
    if (audio?.duration && Number.isFinite(audio.duration)) {
      barDur.textContent = fmt(audio.duration);
    }
  });

  audio.addEventListener("ended", () => playAdjacent(1));
  ticker = setInterval(syncProgress, 200);

  audio.play().catch(() => {
    stopAll();
    setIdle();
  });

  recordRecent(normalized);
}

function filterTracks(tracks, q) {
  if (!q) return tracks;
  const query = q.toLowerCase();
  return tracks.filter((track) => {
    const name = (track.name || "").toLowerCase();
    const artist = (track.artist || "").toLowerCase();
    return name.includes(query) || artist.includes(query);
  });
}

function getViewTitle() {
  if (state.currentView === "liked") return "Liked <em>songs</em>";
  if (state.currentView === "recent") return "Recently <em>played</em>";
  if (state.currentView === "search") return `Search results for <em>${esc(globalSearchInput.value.trim())}</em>`;
  if (state.currentView === "playlists") {
    if (state.currentPlaylistId) {
      const playlist = state.playlists.find((p) => p.id === state.currentPlaylistId);
      if (playlist) return `Playlist: <em>${esc(playlist.name)}</em>`;
    }
    return "Your <em>playlists</em>";
  }
  return state.homeTitle;
}

function getSourceTracks() {
  switch (state.currentView) {
    case "liked":
      return state.likedTracks;
    case "recent":
      return state.recentTracks;
    case "playlists":
      return state.playlistTracks;
    case "search":
      return state.searchTracks;
    default:
      return state.homeTracks;
  }
}

function getEmptyMessage() {
  switch (state.currentView) {
    case "liked":
      return "Like songs and they will show up here.";
    case "recent":
      return "Play songs and your recent history will appear here.";
    case "playlists":
      return "Create a playlist and add tracks from results.";
    case "search":
      return "No search matches yet. Try another artist or song.";
    default:
      return "No songs found yet. Try another mood.";
  }
}

function buildTrackRow(track, index) {
  const normalized = normalizeTrack(track);
  const row = document.createElement("div");
  row.className = "track";
  row.dataset.key = trackKey(normalized);
  row.style.animationDelay = `${index * 0.03}s`;

  const hasPreview = !!normalized.preview_url;
  const hasLastfm = !!normalized.lastfm_url;
  const art = normalized.album_cover
    ? `<img src="${esc(normalized.album_cover)}" alt="${esc(normalized.name)} cover" loading="lazy">`
    : '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg>';

  row.innerHTML = `
    <div class="t-title">
      <div class="t-art">${art}</div>
      <div class="t-info">
        <div class="t-name">${esc(normalized.name)}</div>
        <div class="t-artist-sub">${esc(normalized.artist)}</div>
      </div>
    </div>
    <div class="t-artist-col">${esc(normalized.artist)}</div>
    <div class="t-actions">
      <button class="t-btn prev-btn" ${hasPreview ? "" : "disabled"} title="${hasPreview ? "Play preview" : "No preview"}">
        <svg viewBox="0 0 24 24" fill="currentColor"><path d="${PLAY}"/></svg>
      </button>
      <button class="t-btn like-btn" title="Like song">
        <svg viewBox="0 0 24 24" fill="currentColor"><path d="${HEART_OUTLINE}"/></svg>
      </button>
      <button class="t-btn t-add" title="Add to playlist">
        <svg viewBox="0 0 24 24" fill="currentColor"><path d="${PLUS_ICON}"/></svg>
      </button>
      <a class="t-btn t-lastfm ${hasLastfm ? "" : "is-disabled"}" href="${hasLastfm ? esc(normalized.lastfm_url) : "#"}" target="_blank" rel="noopener" title="Open on Last.fm">Last.fm</a>
    </div>
  `;
  const playBtnEl = row.querySelector(".prev-btn");
  playBtnEl.classList.add("t-play-btn");
  playBtnEl.innerHTML = `<svg viewBox="0 0 24 24" fill="currentColor"><path d="${PLAY}"/></svg><span>${hasPreview ? "Play" : "No Preview"}</span>`;

  const playBtn = playBtnEl;
  const likeBtn = row.querySelector(".like-btn");
  const addBtn = row.querySelector(".t-add");

  setTrackLikeState(likeBtn, normalized);

  if (hasPreview) {
    row.querySelector(".t-title").addEventListener("click", () => playTrack(normalized, row, playBtn));
    playBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      playTrack(normalized, row, playBtn);
    });
  }

  likeBtn.addEventListener("click", async (event) => {
    event.stopPropagation();
    try {
      await toggleLikeTrack(normalized);
    } catch (error) {
      showError(error.message);
    }
  });

  addBtn.addEventListener("click", async (event) => {
    event.stopPropagation();
    await addTrackToPlaylistFlow(normalized);
  });

  if (activeTrack && trackKey(activeTrack) === trackKey(normalized) && audio && !audio.paused && hasPreview) {
    row.classList.add("active");
    setTrackPlayState(playBtn, true);
    activeRow = row;
    activePlayBtn = playBtn;
  } else {
    setTrackPlayState(playBtn, false);
  }

  return row;
}

function renderCurrentView() {
  navLinks.forEach((link) => {
    link.classList.toggle("active", link.dataset.view === state.currentView);
  });

  setComposerVisible(state.currentView === "home");

  if (state.currentView === "home" && !state.hasHomeResults) {
    results.style.display = "none";
    results.classList.remove("on");
    tracksList.innerHTML = "";
    state.currentTracks = [];
    state.renderedTracks = [];
    return;
  }

  const sourceTracks = getSourceTracks().map(normalizeTrack);
  const showFilter = state.currentView === "search" || (state.currentView !== "recent" && sourceTracks.length > 6);
  listFilterInput.style.display = showFilter ? "" : "none";
  const showExportSpotify = state.currentView === "playlists" && !!state.currentPlaylistId && sourceTracks.length > 0;
  exportSpotifyBtn.style.display = showExportSpotify ? "inline-flex" : "none";
  const showClearRecent = state.currentView === "recent" && sourceTracks.length > 0;
  clearRecentBtn.style.display = showClearRecent ? "inline-flex" : "none";
  resultsActions.classList.toggle("only-clear", showClearRecent && !showExportSpotify && !showFilter);
  if (!showFilter && state.filterQuery) {
    state.filterQuery = "";
    listFilterInput.value = "";
  }

  const filteredTracks = filterTracks(sourceTracks, state.filterQuery);
  state.currentTracks = sourceTracks;
  state.renderedTracks = filteredTracks;

  resTitle.innerHTML = getViewTitle();
  tracksList.innerHTML = "";

  if (!filteredTracks.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = getEmptyMessage();
    tracksList.appendChild(empty);
  } else {
    filteredTracks.forEach((track, index) => tracksList.appendChild(buildTrackRow(track, index)));
  }

  results.style.display = "block";
  results.classList.add("on");
  setBarHeartState(activeTrack);
}

async function refreshLikedTracks() {
  const data = await api("/api/liked");
  state.likedTracks = (data.tracks || []).map(normalizeTrack);
  updateLikedCount();
}

async function refreshRecentTracks() {
  const data = await api("/api/recent");
  state.recentTracks = (data.tracks || []).map(normalizeTrack);
}

async function refreshPlaylists() {
  const data = await api("/api/playlists");
  state.playlists = data.playlists || [];
  renderPlaylistsSidebar();
}

async function loadPlaylist(id, moveToPlaylistView = true) {
  const data = await api(`/api/playlists/${id}`);
  state.currentPlaylistId = data.id;
  state.playlistTracks = (data.tracks || []).map(normalizeTrack);
  if (moveToPlaylistView) {
    state.currentView = "playlists";
  }
  renderPlaylistsSidebar();
  renderCurrentView();
}

function renderPlaylistsSidebar() {
  playlistList.innerHTML = "";
  if (!state.playlists.length) {
    const empty = document.createElement("div");
    empty.className = "pl-empty";
    empty.textContent = "No playlists yet";
    playlistList.appendChild(empty);
    return;
  }

  state.playlists.forEach((playlist) => {
    const item = document.createElement("div");
    item.className = "pl-item";
    if (state.currentPlaylistId === playlist.id && state.currentView === "playlists") {
      item.classList.add("active");
    }
    item.innerHTML = `
      <div class="pl-dot">♫</div>
      <div class="pl-meta">
        <div class="pl-name">${esc(playlist.name)}</div>
        <div class="pl-count">${playlist.track_count || 0} songs</div>
      </div>
      <button class="pl-del-btn" title="Delete playlist" data-id="${playlist.id}">×</button>
    `;

    item.addEventListener("click", () => {
      loadPlaylist(playlist.id, true).catch((error) => showError(error.message));
    });

    const delBtn = item.querySelector(".pl-del-btn");
    delBtn.addEventListener("click", async (event) => {
      event.preventDefault();
      event.stopPropagation();
      await deletePlaylistFlow(playlist.id, playlist.name);
    });

    playlistList.appendChild(item);
  });
}

async function deletePlaylistFlow(playlistId, playlistName) {
  const ok = window.confirm(`Delete playlist "${playlistName}"?`);
  if (!ok) return;

  try {
    const data = await api(`/api/playlists/${playlistId}/delete`, { method: "POST" });
    state.playlists = data.playlists || [];

    if (state.currentPlaylistId === playlistId) {
      state.currentPlaylistId = null;
      state.playlistTracks = [];
      if (state.playlists.length) {
        await loadPlaylist(state.playlists[0].id, true);
        return;
      }
      state.currentView = "home";
    }

    renderPlaylistsSidebar();
    renderCurrentView();
  } catch (error) {
    showError(error.message);
  }
}

async function exportCurrentPlaylistToSpotify() {
  if (!state.currentPlaylistId) {
    window.alert("Open a playlist first, then export.");
    return;
  }

  const originalLabel = exportSpotifyBtn.textContent;
  exportSpotifyBtn.disabled = true;
  exportSpotifyBtn.textContent = "Exporting...";

  try {
    const data = await api(`/api/playlists/${state.currentPlaylistId}/export/spotify`, { method: "POST" });
    const matched = data.matched_tracks ?? 0;
    const missed = data.unmatched_tracks ?? 0;
    if (data.spotify_playlist_url) {
      window.open(data.spotify_playlist_url, "_blank", "noopener");
    }
    window.alert(`Exported to Spotify: ${matched} matched${missed ? `, ${missed} not found` : ""}.`);
  } catch (error) {
    if (error.status === 401 && error.data?.auth_url) {
      window.location.href = error.data.auth_url;
      return;
    }
    showError(error.message);
    window.alert(`Spotify export failed: ${error.message}`);
  } finally {
    exportSpotifyBtn.disabled = false;
    exportSpotifyBtn.textContent = originalLabel;
  }
}

function handleSpotifyExportStatusFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const status = params.get("spotify_export");
  if (!status) return;

  if (status === "success") {
    const playlistName = params.get("name") || "Playlist";
    const matched = params.get("matched") || "0";
    const missed = params.get("missed") || "0";
    const url = params.get("url");
    window.alert(`Spotify export complete for "${playlistName}" (${matched} matched, ${missed} missing).`);
    if (url) {
      window.open(url, "_blank", "noopener");
    }
  } else if (status === "connected") {
    window.alert("Spotify connected successfully.");
  } else if (status === "error") {
    const message = params.get("message") || "Spotify export failed.";
    showError(message);
    window.alert(`Spotify export failed: ${message}`);
  }

  const cleanUrl = new URL(window.location.href);
  cleanUrl.search = "";
  window.history.replaceState({}, "", cleanUrl);
}

async function ensurePlaylistForAdd() {
  if (state.currentView === "playlists" && state.currentPlaylistId) {
    return state.currentPlaylistId;
  }

  if (!state.playlists.length) {
    const name = window.prompt("Create a playlist name:", "My Playlist");
    if (!name) return null;
    const data = await api("/api/playlists", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    state.playlists = data.playlists || [];
    renderPlaylistsSidebar();
    return data.playlist.id;
  }

  const options = state.playlists.map((p) => p.name).join(", ");
  const chosenName = window.prompt(`Add to which playlist?\nAvailable: ${options}`, state.playlists[0].name);
  if (!chosenName) return null;

  const existing = state.playlists.find((p) => p.name.toLowerCase() === chosenName.trim().toLowerCase());
  if (existing) return existing.id;

  const created = await api("/api/playlists", {
    method: "POST",
    body: JSON.stringify({ name: chosenName }),
  });
  state.playlists = created.playlists || [];
  renderPlaylistsSidebar();
  return created.playlist.id;
}

async function addTrackToPlaylistFlow(track) {
  try {
    const playlistId = await ensurePlaylistForAdd();
    if (!playlistId) return;

    await api(`/api/playlists/${playlistId}/tracks`, {
      method: "POST",
      body: JSON.stringify({ track }),
    });

    await refreshPlaylists();
    if (state.currentView === "playlists" && state.currentPlaylistId === playlistId) {
      await loadPlaylist(playlistId, false);
    }
  } catch (error) {
    showError(error.message);
  }
}

async function toggleLikeTrack(track) {
  const response = await api("/api/liked/toggle", {
    method: "POST",
    body: JSON.stringify({ track }),
  });

  state.likedTracks = (response.tracks || []).map(normalizeTrack);
  updateLikedCount();
  const likedKeys = likedSet();

  Array.from(document.querySelectorAll(".track")).forEach((row) => {
    const likeBtn = row.querySelector(".like-btn");
    if (!likeBtn) return;
    const liked = likedKeys.has(row.dataset.key || "");
    likeBtn.classList.toggle("active-btn", liked);
    setD(likeBtn.querySelector("path"), liked ? HEART_FILLED : HEART_OUTLINE);
  });

  if (activeTrack) setBarHeartState(activeTrack);

  if (state.currentView === "liked") {
    renderCurrentView();
  }
}

async function setView(view) {
  state.currentView = view;
  state.filterQuery = "";
  listFilterInput.value = "";
  clearError();

  if (view === "liked") {
    await refreshLikedTracks();
  }
  if (view === "recent") {
    await refreshRecentTracks();
  }
  if (view === "playlists" && state.currentPlaylistId) {
    await loadPlaylist(state.currentPlaylistId, false);
    return;
  }

  if (view === "playlists" && state.playlists.length && !state.currentPlaylistId) {
    await loadPlaylist(state.playlists[0].id, false);
    return;
  }

  renderCurrentView();
}

async function runGlobalSearch(force = false) {
  const query = globalSearchInput.value.trim();

  if (!query) {
    if (state.currentView === "search") {
      await setView(state.previousViewBeforeSearch || "home");
    }
    return;
  }

  if (!force && query.length < 2) return;

  try {
    if (state.currentView !== "search") {
      state.previousViewBeforeSearch = state.currentView;
    }

    setLoading(true);
    const data = await api(`/search?q=${encodeURIComponent(query)}`);
    state.searchTracks = (data.tracks || []).map(normalizeTrack);
    state.currentView = "search";
    state.filterQuery = "";
    listFilterInput.value = "";
    emotionRow.classList.remove("on");
    renderCurrentView();
  } catch (error) {
    showError(error.message);
  } finally {
    setLoading(false);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const mood = moodInput.value.trim();
  if (!mood) return;

  clearError();
  setLoading(true);
  submitBtn.disabled = true;
  emotionRow.classList.remove("on");

  stopAll();
  setIdle();

  try {
    const data = await api("/recommend", {
      method: "POST",
      body: JSON.stringify({ text: mood }),
    });

    state.homeTracks = (data.tracks || []).map(normalizeTrack);
    state.hasHomeResults = true;

    if (data.emotion) {
      eDot.className = `e-dot ${data.emotion}`;
      eTextVal.textContent = ELABELS[data.emotion] || data.emotion;
      emotionRow.classList.add("on");
      state.homeTitle = `Your <em>${(ELABELS[data.emotion] || data.emotion).toLowerCase()}</em> playlist`;
    }

    await setView("home");
    results.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    showError(error.message);
  } finally {
    setLoading(false);
    submitBtn.disabled = false;
  }
});

listFilterInput.addEventListener("input", () => {
  state.filterQuery = listFilterInput.value.trim();
  renderCurrentView();
});

globalSearchInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    clearTimeout(state.searchDebounce);
    runGlobalSearch(true);
  }
});

globalSearchInput.addEventListener("input", () => {
  clearTimeout(state.searchDebounce);
  state.searchDebounce = setTimeout(() => {
    runGlobalSearch(false);
  }, 350);
});

newPlaylistBtn.addEventListener("click", async () => {
  const name = window.prompt("Playlist name:", "My Playlist");
  if (!name) return;

  try {
    const data = await api("/api/playlists", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    state.playlists = data.playlists || [];
    renderPlaylistsSidebar();
    if (data.playlist?.id) {
      await loadPlaylist(data.playlist.id, true);
    }
  } catch (error) {
    showError(error.message);
  }
});

authBtn?.addEventListener("click", () => {
  startAuthFlow().catch((error) => showError(error.message));
});

exportSpotifyBtn.addEventListener("click", async () => {
  await exportCurrentPlaylistToSpotify();
});

clearRecentBtn.addEventListener("click", async () => {
  const ok = window.confirm("Clear all recently played songs?");
  if (!ok) return;

  try {
    await api("/api/recent/clear", { method: "POST" });
    state.recentTracks = [];
    renderCurrentView();
  } catch (error) {
    showError(error.message);
    window.alert(`Could not clear recently played: ${error.message}`);
  }
});

navLinks.forEach((link) => {
  link.addEventListener("click", (event) => {
    event.preventDefault();
    setView(link.dataset.view).catch((error) => showError(error.message));
  });
});

mainEl.addEventListener("scroll", () => {
  topbar.classList.toggle("stuck", mainEl.scrollTop > 50);
});

barPlayBtn.addEventListener("click", toggleCurrentPlay);
barPrevBtn.addEventListener("click", () => playAdjacent(-1));
barNextBtn.addEventListener("click", () => playAdjacent(1));

barHeartBtn.addEventListener("click", async () => {
  if (!activeTrack) return;
  try {
    await toggleLikeTrack(activeTrack);
  } catch (error) {
    showError(error.message);
  }
});

barTrack.addEventListener("click", (event) => {
  if (!audio?.duration) return;
  const rect = barTrack.getBoundingClientRect();
  audio.currentTime = ((event.clientX - rect.left) / rect.width) * audio.duration;
  syncProgress();
});

barVol?.addEventListener("mousedown", (event) => {
  isDraggingVolume = true;
  updateVolumeFromPointer(event.clientX);
});

window.addEventListener("mousemove", (event) => {
  if (!isDraggingVolume) return;
  updateVolumeFromPointer(event.clientX);
});

window.addEventListener("mouseup", () => {
  isDraggingVolume = false;
});

barVol?.addEventListener("click", (event) => {
  updateVolumeFromPointer(event.clientX);
});

document.addEventListener("keydown", (event) => {
  const isShortcutFocus = (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k";
  const inField = event.target.closest("input, textarea, select, button, [contenteditable='true']");

  if (isShortcutFocus) {
    event.preventDefault();
    globalSearchInput.focus();
    globalSearchInput.select();
    return;
  }

  if (inField) return;

  if (event.code === "Space") {
    event.preventDefault();
    toggleCurrentPlay();
    return;
  }

  if (event.key === "ArrowRight") {
    event.preventDefault();
    playAdjacent(1);
    return;
  }

  if (event.key === "ArrowLeft") {
    event.preventDefault();
    playAdjacent(-1);
    return;
  }

  if (event.key.toLowerCase() === "l" && activeTrack) {
    event.preventDefault();
    toggleLikeTrack(activeTrack).catch((error) => showError(error.message));
  }
});

async function init() {
  setIdle();
  updateVolumeUI();
  setLoading(false);
  clearError();

  try {
    await initSupabaseAuth();
    const data = await api("/api/bootstrap");
    state.likedTracks = (data.liked_tracks || []).map(normalizeTrack);
    state.recentTracks = (data.recent_tracks || []).map(normalizeTrack);
    state.playlists = data.playlists || [];
    if (data.auth_required) {
      showError("Sign in to sync liked songs, recents, and playlists across users.");
    }
    updateLikedCount();
    renderPlaylistsSidebar();
    renderCurrentView();
    handleSpotifyExportStatusFromUrl();
  } catch (error) {
    showError(error.message);
  }
}

init();
