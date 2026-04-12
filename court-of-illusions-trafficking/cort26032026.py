#!/usr/bin/env python3
from pathlib import Path
import sys
import re
import shutil
from html import unescape

INJECTION = r"""
<script id="report-chatlog-enhancer">
document.addEventListener("DOMContentLoaded", () => {
  const chatlog = document.querySelector(".chatlog");
  if (!chatlog) return;

  document.body.id = "top";

  const groups = Array.from(chatlog.querySelectorAll(".chatlog__message-group"));

  const MONTHS = {
    january: 0,
    february: 1,
    march: 2,
    april: 3,
    may: 4,
    june: 5,
    july: 6,
    august: 7,
    september: 8,
    october: 9,
    november: 10,
    december: 11
  };

  function normalizeWhitespace(text) {
    return (text || "")
      .replace(/\u00a0/g, " ")
      .replace(/[ \t]+\n/g, "\n")
      .replace(/\n[ \t]+/g, "\n")
      .replace(/\n{3,}/g, "\n\n")
      .replace(/[ \t]{2,}/g, " ")
      .replace(/\s+([,.;:!?])/g, "$1")
      .trim();
  }

  function normalizeInlineWhitespace(text) {
    return normalizeWhitespace(text).replace(/\n+/g, " ").trim();
  }

  function capitalizeWords(text) {
    return text.replace(
      /\b([a-z\u00c0-\u024f\u0400-\u04ff])([a-z\u00c0-\u024f\u0400-\u04ff]*)/gi,
      (_, first, rest) => first.toUpperCase() + rest.toLowerCase()
    );
  }

  function isEmojiLikeText(text) {
    if (!text) return false;
    try {
      return /[\p{Extended_Pictographic}\u200D\uFE0F]/u.test(text);
    } catch {
      return /[\u2190-\u2BFF\u2600-\u27BF]/.test(text);
    }
  }

  function isTinyDimension(value) {
    if (!value) return false;
    const num = Number.parseFloat(value);
    return Number.isFinite(num) && num > 0 && num <= 64;
  }

  function isEmojiImage(img) {
    if (!img) return false;

    const className = (img.className || "").toString();
    const alt = img.getAttribute("alt") || "";
    const aria = img.getAttribute("aria-label") || "";
    const src = img.getAttribute("src") || "";
    const title = img.getAttribute("title") || "";
    const widthAttr = img.getAttribute("width");
    const heightAttr = img.getAttribute("height");

    if (/\b(emoji|emote|twemoji|custom-emoji|chatlog__emoji|chatlog__custom-emoji)\b/i.test(className)) {
      return true;
    }

    if (/\/emoji\/|\/emojis\/|\/twemoji\/|\/assets\/emojis\//i.test(src)) {
      return true;
    }

    if (isEmojiLikeText(alt) || isEmojiLikeText(aria) || isEmojiLikeText(title)) {
      return true;
    }

    const naturalWidth = img.naturalWidth || 0;
    const naturalHeight = img.naturalHeight || 0;
    const renderedWidth = img.width || 0;
    const renderedHeight = img.height || 0;

    const tinyByAttr = isTinyDimension(widthAttr) && isTinyDimension(heightAttr);
    const tinyByNatural = naturalWidth > 0 && naturalHeight > 0 && naturalWidth <= 64 && naturalHeight <= 64;
    const tinyByRendered = renderedWidth > 0 && renderedHeight > 0 && renderedWidth <= 48 && renderedHeight <= 48;

    if ((tinyByAttr || tinyByNatural || tinyByRendered) && (alt || aria || title || /\bemoji\b/i.test(className))) {
      return true;
    }

    return false;
  }

  function collectRenderableTextFromNode(root) {
    if (!root) return "";

    const clone = root.cloneNode(true);

    clone.querySelectorAll("img").forEach(img => {
      if (isEmojiImage(img)) {
        const alt = img.getAttribute("alt") || img.getAttribute("aria-label") || "";
        img.replaceWith(document.createTextNode(alt ? ` ${alt} ` : " "));
      } else {
        img.remove();
      }
    });

    clone.querySelectorAll(
      ".chatlog__author, .chatlog__author-name, .chatlog__timestamp, .chatlog__short-timestamp, " +
      ".chatlog__edited-timestamp, .chatlog__attachment, .chatlog__attachment-generic, .chatlog__embed, " +
      ".chatlog__reference, .chatlog__reply, .chatlog__reactions, .chatlog__sticker, audio, video, iframe, " +
      "object, embed, .pre--multiline, pre, code, .report-summary, .post-return-wrap"
    ).forEach(el => el.remove());

    return normalizeWhitespace(clone.textContent || "");
  }

  function extractContentDate(group) {
    const text = collectRenderableTextFromNode(group);
    if (!text) return null;

    let match = text.match(/\b(\d{1,2})\/(\d{1,2})\/(\d{4})\b/);
    if (match) {
      const day = Number(match[1]);
      const month = Number(match[2]) - 1;
      const year = Number(match[3]);
      return new Date(year, month, day);
    }

    match = text.match(/\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b/i);
    if (match) {
      const day = Number(match[1]);
      const month = MONTHS[match[2].toLowerCase()];
      const year = Number(match[3]);
      return new Date(year, month, day);
    }

    match = text.match(/\b(\d{1,2})[–-](\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b/i);
    if (match) {
      const day = Number(match[1]);
      const month = MONTHS[match[3].toLowerCase()];
      const year = Number(match[4]);
      return new Date(year, month, day);
    }

    return null;
  }

  function buildTitleFromText(text) {
    const cleaned = normalizeWhitespace(text);
    if (!cleaned) return "Untitled Entry";

    const lines = cleaned
      .split("\n")
      .map(line => normalizeInlineWhitespace(line))
      .filter(Boolean);

    let firstLine = lines[0] || cleaned;

    firstLine = firstLine.replace(/^[•\-–—]\s*/, "").trim();

    let dateLead = "";
    let remainder = firstLine;

    let match = firstLine.match(/^(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\s*[—–-]\s*(.+)$/i);
    if (match) {
      dateLead = match[1];
      remainder = match[2];
    } else {
      match = firstLine.match(/^(\d{1,2}\/\d{1,2}\/\d{4})\s*[—–-]\s*(.+)$/i);
      if (match) {
        dateLead = match[1];
        remainder = match[2];
      }
    }

    if (!dateLead) {
      const rangeMatch = firstLine.match(/^(.+?[A-Za-z])\s*[–-]\s*(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})$/i);
      if (rangeMatch) {
        return normalizeInlineWhitespace(firstLine).slice(0, 120);
      }
    }

    remainder = normalizeInlineWhitespace(remainder);

    if (!remainder) {
      return normalizeInlineWhitespace(firstLine).slice(0, 120);
    }

    const words = remainder.split(/\s+/);
    let headline = words.slice(0, 10).join(" ");
    headline = headline.replace(/[,:;.\-–—]+$/, "").trim();

    let result = dateLead ? `${dateLead} — ${headline}` : headline;
    if (result.length > 120) {
      result = result.slice(0, 117).trim().replace(/[,:;.\-–—]+$/, "").trim() + "…";
    }

    return result || "Untitled Entry";
  }

  function collectSummarySource(group) {
    return collectRenderableTextFromNode(group);
  }

  function summarizeText(text, minLen = 400, maxLen = 500) {
    const cleaned = normalizeInlineWhitespace(text);

    if (!cleaned) {
      return "No text summary available for this entry. This post appears to be primarily visual or attachment-based.";
    }

    if (cleaned.length <= maxLen) {
      return cleaned;
    }

    const sentenceMatches = cleaned.match(/[^.!?]+[.!?]+(?:\s|$)|[^.!?]+$/g) || [cleaned];
    let built = "";

    for (const sentence of sentenceMatches) {
      const next = normalizeInlineWhitespace((built ? built + " " : "") + sentence);
      if (next.length <= maxLen) {
        built = next;
        if (built.length >= minLen) {
          return built;
        }
      } else {
        break;
      }
    }

    if (built.length >= minLen) {
      return built;
    }

    let slice = cleaned.slice(0, maxLen + 1);
    let cut = Math.max(
      slice.lastIndexOf(". "),
      slice.lastIndexOf("! "),
      slice.lastIndexOf("? "),
      slice.lastIndexOf("; "),
      slice.lastIndexOf(": "),
      slice.lastIndexOf(", "),
      slice.lastIndexOf(" ")
    );

    if (cut < minLen) {
      cut = maxLen;
    }

    let result = cleaned.slice(0, cut).trim();
    result = result.replace(/[,:;\-–—]+$/, "").trim();

    if (result.length < cleaned.length) {
      result += "…";
    }

    return result;
  }

  function decodeFilenamePart(value) {
    try {
      return decodeURIComponent(value);
    } catch {
      return value;
    }
  }

  function extractFilenameFromLink(link) {
    if (!link) return "";

    const hrefAttr = link.getAttribute("href") || "";
    const rawText = normalizeInlineWhitespace(link.textContent || "");

    let candidate = hrefAttr || rawText;
    if (!candidate) return "";

    candidate = candidate.split("#")[0].split("?")[0];
    const parts = candidate.split("/").filter(Boolean);
    const lastPart = parts.length ? parts[parts.length - 1] : candidate;

    const decoded = decodeFilenamePart(lastPart).trim();
    if (decoded) return decoded;

    return rawText;
  }

  function buildAttachmentButtonLabel(link) {
    const filename = extractFilenameFromLink(link);
    const lower = filename.toLowerCase();

    if (lower.endsWith(".pdf")) {
      return `PDF — ${filename}`;
    }
    if (lower.endsWith(".srt")) {
      return `Subtitles — ${filename}`;
    }
    if (lower.endsWith(".mp3")) {
      return `MP3 — ${filename}`;
    }

    return filename || "Attachment";
  }

  groups.sort((a, b) => {
    const dateA = extractContentDate(a);
    const dateB = extractContentDate(b);

    if (!dateA && !dateB) return 0;
    if (!dateA) return 1;
    if (!dateB) return -1;

    return dateA - dateB;
  });

  chatlog.replaceChildren(...groups);

  document.querySelectorAll(".chatlog__attachment-generic-name a").forEach(link => {
    link.textContent = buildAttachmentButtonLabel(link);
  });

  document.querySelectorAll(".chatlog__edited-timestamp").forEach(el => el.remove());

  document.querySelectorAll(".chatlog__content img, .chatlog__markdown-preserve img").forEach(img => {
    if (isEmojiImage(img)) {
      img.classList.add("veilocity-inline-emoji");
    } else {
      img.classList.remove("veilocity-inline-emoji");
      img.classList.add("veilocity-report-image");
    }
  });

  document.querySelectorAll(".chatlog__attachment-generic").forEach(card => {
    const parent = card.parentElement;
    if (parent) {
      parent.classList.add("media-row");
    }
  });

  document.querySelectorAll(".chatlog__message-group").forEach((group, index) => {
    const header = group.querySelector(".chatlog__header");
    const author = group.querySelector(".chatlog__author");
    const authorName = group.querySelector(".chatlog__author-name");
    const timestamp = group.querySelector(".chatlog__timestamp");
    const firstContainer = group.querySelector(".chatlog__message-container");
    const firstContent = group.querySelector(".chatlog__content");
    const preserve = group.querySelector(".chatlog__markdown-preserve");
    const strong = group.querySelector(".chatlog__content strong");

    const summarySourceBeforeChanges = collectSummarySource(group);
    const titleTextPlain = strong
      ? normalizeInlineWhitespace(strong.textContent || "")
      : buildTitleFromText(summarySourceBeforeChanges);

    let anchorId = "";
    if (firstContainer && firstContainer.id) {
      anchorId = firstContainer.id;
    } else {
      anchorId = `report-entry-${index + 1}`;
      group.id = anchorId;
    }

    if (header) {
      let titleRow = header.querySelector(".chatlog__title-row");
      if (!titleRow) {
        titleRow = document.createElement("div");
        titleRow.className = "chatlog__title-row";
        header.prepend(titleRow);
      }

      let titleEl = titleRow.querySelector(".chatlog__title-replacement");
      if (!titleEl) {
        titleEl = document.createElement("a");
        titleEl.className = "chatlog__title-replacement";
        titleRow.appendChild(titleEl);
      }

      if (strong) {
        titleEl.innerHTML = strong.innerHTML;
      } else {
        titleEl.textContent = titleTextPlain;
      }
      titleEl.setAttribute("href", `#${anchorId}`);
    }

    if (author) author.remove();
    if (authorName) authorName.remove();
    if (timestamp) timestamp.remove();
    if (strong) strong.remove();

    if (preserve) {
      preserve.innerHTML = preserve.innerHTML
        .replace(/^(?:\s|&nbsp;|<br\s*\/?>)+/i, "")
        .replace(/^(?:\u00a0|\s)+/i, "");
    }

    if (firstContent) {
      firstContent.innerHTML = firstContent.innerHTML
        .replace(/^(?:\s|&nbsp;|<br\s*\/?>)+/i, "")
        .replace(/^(?:\u00a0|\s)+/i, "");
    }

    let existingSummary = group.querySelector(".report-summary");
    if (existingSummary) existingSummary.remove();

    const summaryText = summarizeText(summarySourceBeforeChanges, 400, 500);
    group.dataset.summary = summaryText;
    group.dataset.reportTitle = titleTextPlain;

    const summaryBox = document.createElement("div");
    summaryBox.className = "report-summary";

    const summaryLabel = document.createElement("div");
    summaryLabel.className = "report-summary__label";
    summaryLabel.textContent = "Summary";

    const summaryBody = document.createElement("div");
    summaryBody.className = "report-summary__text";
    summaryBody.textContent = summaryText;

    summaryBox.appendChild(summaryLabel);
    summaryBox.appendChild(summaryBody);
    group.appendChild(summaryBox);
  });

  const style = document.createElement("style");
  style.textContent = `
    :root {
      --bg-1: #e7d8c2;
      --bg-2: #cbb79e;
      --panel: rgba(255, 248, 235, 0.78);
      --panel-2: rgba(245, 230, 210, 0.92);
      --line: rgba(110, 88, 64, 0.18);
      --line-strong: rgba(110, 88, 64, 0.32);
      --text: #3c332c;
      --muted: #6e5f4d;
      --accent: #d86a3c;
      --accent-2: #f08a2b;
      --accent-3: #2f6e62;
      --glow: 0 0 22px rgba(240, 138, 43, 0.14);
      --radius: 16px;
    }

    html, body {
      background:
        radial-gradient(circle at top left, rgba(240, 138, 43, 0.16), transparent 32%),
        radial-gradient(circle at top right, rgba(216, 106, 60, 0.12), transparent 28%),
        linear-gradient(180deg, var(--bg-1) 0%, var(--bg-2) 100%) !important;
      color: var(--text) !important;
      scroll-behavior: smooth;
    }

    body {
      font-family: Inter, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
      letter-spacing: 0.01em;
    }

    .chatlog {
      max-width: 1200px;
      margin: 0 auto;
      padding: 0 18px 48px;
    }

    .chatlog__message-group {
      margin: 18px 0 !important;
      padding: 16px 18px !important;
      background: linear-gradient(180deg, rgba(255, 250, 241, 0.90), rgba(242, 225, 201, 0.95)) !important;
      border: 1px solid var(--line) !important;
      border-radius: var(--radius) !important;
      box-shadow:
        0 10px 24px rgba(60, 51, 44, 0.12),
        inset 0 1px 0 rgba(255, 255, 255, 0.45),
        var(--glow) !important;
      backdrop-filter: blur(8px);
      transition: none !important;
      transform: none !important;
      filter: none !important;
    }

    .chatlog__message-group:hover,
    .chatlog__message-group:focus,
    .chatlog__message-group:active {
      background: linear-gradient(180deg, rgba(255, 250, 241, 0.90), rgba(242, 225, 201, 0.95)) !important;
      border: 1px solid var(--line) !important;
      box-shadow:
        0 10px 24px rgba(60, 51, 44, 0.12),
        inset 0 1px 0 rgba(255, 255, 255, 0.45),
        var(--glow) !important;
      transform: none !important;
      filter: none !important;
      color: var(--text) !important;
    }

    .chatlog__author-avatar-container,
    .chatlog__avatar {
      visibility: hidden !important;
      width: 0 !important;
      min-width: 0 !important;
    }

    .chatlog__messages {
      margin-left: 0 !important;
      background: transparent !important;
      box-shadow: none !important;
      filter: none !important;
      transform: none !important;
    }

    .chatlog__message,
    .chatlog__message:hover,
    .chatlog__message:focus,
    .chatlog__message:active,
    .chatlog__messages,
    .chatlog__messages:hover,
    .chatlog__messages:focus,
    .chatlog__messages:active,
    .chatlog__content,
    .chatlog__content:hover,
    .chatlog__content:focus,
    .chatlog__content:active {
      background: transparent !important;
      box-shadow: none !important;
      filter: none !important;
      transform: none !important;
    }

    .chatlog__header {
      display: block !important;
      margin-bottom: 8px !important;
      padding-bottom: 0 !important;
    }

    .chatlog__title-row {
      display: block !important;
      margin: 0 !important;
      padding: 0 !important;
      line-height: 1.2 !important;
    }

    .chatlog__title-replacement,
    .chatlog__title-replacement:link,
    .chatlog__title-replacement:visited {
      display: inline-block !important;
      color: #000000 !important;
      -webkit-text-fill-color: #000000 !important;
      font-size: 1.02rem !important;
      font-weight: 700 !important;
      line-height: 1.2 !important;
      letter-spacing: 0 !important;
      text-shadow: none !important;
      text-decoration: none !important;
      margin: 0 !important;
      padding: 0 !important;
    }

    .chatlog__title-replacement:hover,
    .chatlog__title-replacement:focus {
      text-decoration: underline !important;
      color: #000000 !important;
      -webkit-text-fill-color: #000000 !important;
    }

    .chatlog__content {
      color: var(--text) !important;
      line-height: 1.6;
      font-size: 0.98rem;
      margin-top: 0 !important;
      padding-top: 0 !important;
    }

    .chatlog__markdown-preserve {
      display: block !important;
      margin-top: 0 !important;
      padding-top: 0 !important;
      line-height: 1.6 !important;
    }

    .chatlog__content > .chatlog__markdown-preserve:first-child {
      margin-top: 0 !important;
      padding-top: 0 !important;
    }

    .chatlog__header + .chatlog__content {
      margin-top: 0 !important;
      padding-top: 0 !important;
    }

    .chatlog__content strong {
      color: #2f2923 !important;
    }

    .chatlog__attachment,
    .chatlog__embed,
    .chatlog__reference,
    .pre--multiline {
      border-radius: 14px !important;
      border: 1px solid rgba(110, 88, 64, 0.14) !important;
      background: rgba(255, 246, 233, 0.85) !important;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.35);
      transition: none !important;
      transform: none !important;
      filter: none !important;
    }

    .media-row {
      display: flex !important;
      flex-direction: row !important;
      flex-wrap: wrap !important;
      align-items: center !important;
      gap: 10px !important;
    }

    .media-row > .chatlog__attachment-generic,
    .media-row > .mp3-download {
      width: auto !important;
      min-width: 140px !important;
      max-width: 100% !important;
      min-height: 0 !important;
      height: 44px !important;
      box-sizing: border-box !important;
    }

    .chatlog__attachment-generic {
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
      padding: 0 14px !important;
      border-radius: 14px !important;
      border: 1px solid rgba(110, 88, 64, 0.14) !important;
      background: rgba(250, 239, 223, 0.90) !important;
      transition:
        background 0.15s ease,
        border-color 0.15s ease,
        box-shadow 0.15s ease,
        transform 0.08s ease !important;
      transform: none !important;
      filter: none !important;
      max-width: 100% !important;
    }

    .chatlog__attachment-generic:hover {
      background: rgba(252, 240, 223, 0.95) !important;
      border-color: rgba(216, 106, 60, 0.28) !important;
      box-shadow: 0 4px 10px rgba(240, 138, 43, 0.08) !important;
      transform: translateY(-1px) !important;
    }

    .chatlog__attachment-generic:active {
      background: rgba(245, 231, 212, 0.98) !important;
      border-color: rgba(216, 106, 60, 0.34) !important;
      transform: translateY(0) !important;
    }

    .chatlog__attachment-generic-icon,
    .chatlog__attachment-generic-size {
      display: none !important;
    }

    .chatlog__attachment-generic-name {
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
      margin: 0 !important;
      font-size: 0.95rem !important;
      line-height: 1 !important;
      width: 100% !important;
      text-align: center !important;
      min-width: 0 !important;
    }

    .chatlog__attachment-generic-name a,
    .chatlog__content a,
    .chatlog__attachment-generic-name a:link,
    .chatlog__content a:link,
    .chatlog__attachment-generic-name a:visited,
    .chatlog__content a:visited,
    .chatlog__attachment-generic-name a:hover,
    .chatlog__content a:hover,
    .chatlog__attachment-generic-name a:focus,
    .chatlog__content a:focus,
    .chatlog__attachment-generic-name a:active,
    .chatlog__content a:active {
      color: var(--accent-3) !important;
      -webkit-text-fill-color: var(--accent-3) !important;
      text-decoration: none !important;
      background: transparent !important;
      box-shadow: none !important;
      outline: none !important;
      border-color: transparent !important;
      transition: none !important;
      filter: none !important;
      transform: none !important;
      width: 100% !important;
      text-align: center !important;
      white-space: nowrap !important;
      overflow: hidden !important;
      text-overflow: ellipsis !important;
      display: block !important;
    }

    .report-summary {
      margin-top: 14px !important;
      padding: 14px 16px !important;
      border-radius: 14px !important;
      border: 1px solid rgba(110, 88, 64, 0.14) !important;
      background: linear-gradient(180deg, rgba(255, 244, 230, 0.90), rgba(246, 231, 208, 0.95)) !important;
      box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.42),
        0 6px 18px rgba(60, 51, 44, 0.06) !important;
    }

    .report-summary__label {
      margin-bottom: 7px !important;
      font-size: 0.74rem !important;
      font-weight: 700 !important;
      letter-spacing: 0.08em !important;
      text-transform: uppercase !important;
      color: var(--muted) !important;
    }

    .report-summary__text {
      font-size: 0.94rem !important;
      line-height: 1.55 !important;
      color: var(--text) !important;
    }

    .veilocity-report-image,
    img:not(.veilocity-inline-emoji) {
      display: block !important;
      max-width: min(720px, 100%) !important;
      width: auto !important;
      height: auto !important;
      border-radius: 14px !important;
      box-shadow: 0 8px 24px rgba(60, 51, 44, 0.18) !important;
      margin-top: 10px !important;
    }

    .veilocity-inline-emoji,
    .chatlog__content .veilocity-inline-emoji,
    .chatlog__markdown-preserve .veilocity-inline-emoji {
      display: inline-block !important;
      width: 1.35em !important;
      height: 1.35em !important;
      max-width: 1.35em !important;
      max-height: 1.35em !important;
      min-width: 1.35em !important;
      min-height: 1.35em !important;
      vertical-align: -0.2em !important;
      object-fit: contain !important;
      border-radius: 0 !important;
      box-shadow: none !important;
      padding: 0 !important;
      margin: 0 0.06em !important;
      background: transparent !important;
      filter: none !important;
      transform: none !important;
    }

    .preamble {
      position: relative !important;
      align-items: flex-start !important;
      gap: 20px !important;
      padding: 22px !important;
      padding-right: 150px !important;
      margin: 22px auto 28px !important;
      max-width: 1200px;
      min-height: 170px;
      border-radius: 22px;
      background:
        linear-gradient(180deg, rgba(250, 240, 225, 0.88), rgba(236, 216, 190, 0.95));
      border: 1px solid rgba(110, 88, 64, 0.16);
      box-shadow:
        0 18px 32px rgba(60, 51, 44, 0.14),
        inset 0 1px 0 rgba(255,255,255,0.45),
        0 0 26px rgba(240, 138, 43, 0.08);
      backdrop-filter: blur(8px);
      transition: none !important;
      transform: none !important;
      filter: none !important;
    }

    .preamble__guild-icon {
      max-width: 280px !important;
      max-height: 280px !important;
      width: 280px !important;
      height: auto !important;
      display: block !important;
      border-radius: 18px;
      border: 1px solid rgba(110, 88, 64, 0.20);
      box-shadow:
        0 0 20px rgba(240, 138, 43, 0.08),
        0 8px 20px rgba(60, 51, 44, 0.14);
    }

    .preamble__guild-icon-container {
      max-width: 280px !important;
    }

    .preamble__entries-container {
      margin-left: 1.25rem !important;
      padding-top: 2px !important;
    }

    .preamble__entry {
      color: var(--muted) !important;
    }

    .preamble__entry:first-child {
      font-size: 0.72rem !important;
      line-height: 1.05 !important;
      letter-spacing: 0.08em !important;
      text-transform: uppercase !important;
      color: rgba(60, 51, 44, 0.28) !important;
      -webkit-text-fill-color: rgba(60, 51, 44, 0.28) !important;
      text-shadow: none !important;
      margin-bottom: 8px !important;
      font-weight: 500 !important;
    }

    .preamble__entry:nth-child(2) {
      font-size: 1.28rem !important;
      font-weight: 700 !important;
      color: var(--accent-3) !important;
      letter-spacing: 0.02em;
      text-shadow: 0 0 10px rgba(47, 110, 98, 0.08);
      margin-top: 0 !important;
    }

    .flag-block {
      position: absolute;
      top: 22px;
      right: 22px;
      margin: 0 !important;
      display: flex;
      justify-content: flex-end;
      align-items: flex-start;
      z-index: 2;
    }

    .flag-image {
      display: block;
      width: 96px;
      max-width: 100%;
      height: auto;
      border-radius: 14px;
      border: 1px solid rgba(110, 88, 64, 0.20);
      box-shadow:
        0 8px 20px rgba(60, 51, 44, 0.12),
        0 0 18px rgba(240, 138, 43, 0.05);
      background: rgba(255,255,255,0.35);
      padding: 4px;
    }

    .toc-block {
      margin-top: 18px;
      padding-top: 16px;
      border-top: 1px solid rgba(110, 88, 64, 0.14);
    }

    .toc-title {
      margin: 0 0 14px 0;
      font-size: 0.92rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--muted);
    }

    .toc-list {
      margin: 0;
      padding: 0;
      list-style: none;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px 24px;
    }

    .toc-item {
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid rgba(110, 88, 64, 0.12);
      background: rgba(255, 248, 236, 0.72);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.35);
      min-width: 0;
    }

    .toc-item-title,
    .toc-item-title:link,
    .toc-item-title:visited {
      display: inline-block;
      margin-bottom: 8px;
      color: var(--accent-3) !important;
      -webkit-text-fill-color: var(--accent-3) !important;
      text-decoration: none !important;
      font-size: 0.95rem;
      font-weight: 700;
      line-height: 1.35;
    }

    .toc-item-title:hover,
    .toc-item-title:focus {
      text-decoration: underline !important;
    }

    .toc-item-summary {
      color: var(--text);
      font-size: 0.86rem;
      line-height: 1.5;
      word-break: break-word;
    }

    @media (max-width: 900px) {
      .toc-list {
        grid-template-columns: 1fr;
      }
    }

    .post-return-wrap {
      display: flex !important;
      justify-content: flex-end !important;
      margin-top: 14px !important;
      padding-top: 6px !important;
      width: 100% !important;
    }

    .post-return-link,
    .post-return-link:link,
    .post-return-link:visited {
      display: inline-flex !important;
      align-items: center !important;
      justify-content: center !important;
      padding: 7px 12px !important;
      border-radius: 999px !important;
      border: 1px solid rgba(110, 88, 64, 0.16) !important;
      background: rgba(250, 239, 223, 0.92) !important;
      color: var(--accent-3) !important;
      -webkit-text-fill-color: var(--accent-3) !important;
      text-decoration: none !important;
      font-size: 0.84rem !important;
      line-height: 1 !important;
      box-shadow: 0 2px 8px rgba(60, 51, 44, 0.06) !important;
      visibility: visible !important;
      opacity: 1 !important;
    }

    .post-return-link:hover,
    .post-return-link:focus {
      text-decoration: none !important;
      background: rgba(252, 240, 223, 0.98) !important;
      border-color: rgba(216, 106, 60, 0.24) !important;
      transform: translateY(-1px) !important;
    }

    .post-return-link:active {
      transform: translateY(0) !important;
    }

    .btc-note {
      margin-top: 14px;
      padding: 14px 16px;
      max-width: 280px;
      color: var(--text);
      font-size: 0.92rem;
      line-height: 1.45;
      word-break: break-word;
      background: linear-gradient(180deg, rgba(255, 244, 230, 0.95), rgba(244, 228, 205, 0.98));
      border: 1px solid rgba(216, 106, 60, 0.28);
      border-radius: 14px;
      box-shadow:
        inset 0 1px 0 rgba(255,255,255,0.45),
        0 0 18px rgba(240, 138, 43, 0.06);
      transition: none !important;
    }

    .btc-note strong {
      color: var(--accent);
    }

    .btc-address {
      display: block;
      margin-top: 8px;
      padding: 10px 12px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.82rem;
      line-height: 1.45;
      color: #4a392e;
      background: rgba(240, 138, 43, 0.10);
      border: 1px solid rgba(216, 106, 60, 0.20);
      border-radius: 10px;
      overflow-wrap: anywhere;
    }

    .mp3-download {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 0 14px;
      border: 1px solid rgba(110, 88, 64, 0.14);
      border-radius: 14px;
      background: rgba(255, 246, 233, 0.85) !important;
      text-decoration: none !important;
      color: var(--accent-3) !important;
      -webkit-text-fill-color: var(--accent-3) !important;
      font-weight: 500;
      font-size: 0.95rem;
      line-height: 1;
      transition:
        background 0.15s ease,
        border-color 0.15s ease,
        box-shadow 0.15s ease,
        transform 0.08s ease !important;
      transform: none !important;
      filter: none !important;
    }

    .chatlog__message-group * {
      background-color: transparent !important;
    }

    .chatlog__message-group .pre--multiline,
    .chatlog__message-group .chatlog__attachment,
    .chatlog__message-group .chatlog__embed,
    .chatlog__message-group .chatlog__reference,
    .chatlog__message-group .chatlog__attachment-generic,
    .chatlog__message-group .mp3-download,
    .chatlog__message-group .post-return-link,
    .chatlog__message-group .report-summary {
      background: rgba(255, 246, 233, 0.85) !important;
    }

    * {
      -webkit-tap-highlight-color: transparent !important;
      caret-color: var(--text) !important;
    }

    *:focus,
    *:active {
      outline: none !important;
      box-shadow: none !important;
    }

    a,
    a:link,
    a:visited,
    a:hover,
    a:focus,
    a:active,
    .chatlog a,
    .chatlog a:link,
    .chatlog a:visited,
    .chatlog a:hover,
    .chatlog a:focus,
    .chatlog a:active,
    .chatlog__content a,
    .chatlog__content a:link,
    .chatlog__content a:visited,
    .chatlog__content a:hover,
    .chatlog__content a:focus,
    .chatlog__content a:active,
    .chatlog__attachment-generic-name a,
    .chatlog__attachment-generic-name a:link,
    .chatlog__attachment-generic-name a:visited,
    .chatlog__attachment-generic-name a:hover,
    .chatlog__attachment-generic-name a:focus,
    .chatlog__attachment-generic-name a:active {
      color: var(--accent-3) !important;
      -webkit-text-fill-color: var(--accent-3) !important;
      background: transparent !important;
      text-decoration: none !important;
      outline: none !important;
      box-shadow: none !important;
      border-color: transparent !important;
      filter: none !important;
      transition: none !important;
    }

    ::selection {
      background: rgba(240, 138, 43, 0.22);
      color: #3c332c;
    }
  `;
  document.head.appendChild(style);

  const preamble = document.querySelector(".preamble");
  const brandLine = document.querySelector(".preamble__entry:first-child");
  const channelLine = document.querySelector(".preamble__entry:nth-child(2)");

  if (brandLine) {
    brandLine.textContent = "Report";
  }

  if (channelLine) {
    const cleaned = channelLine.textContent.replace(/^Text Channels\s*\/\s*/i, "").trim();
    channelLine.textContent = capitalizeWords(cleaned);
  }

  if (preamble) {
    let existing = preamble.querySelector(".flag-block");
    if (existing) existing.remove();

    const flagSrc = document.body.dataset.flagSrc;
    if (flagSrc) {
      const flagBlock = document.createElement("div");
      flagBlock.className = "flag-block";

      const img = document.createElement("img");
      img.className = "flag-image";
      img.src = flagSrc;
      img.alt = "Country flag";

      flagBlock.appendChild(img);
      preamble.appendChild(flagBlock);
    }

    let existingToc = preamble.querySelector(".toc-block");
    if (existingToc) existingToc.remove();

    const reportItems = Array.from(document.querySelectorAll(".chatlog__message-group"))
      .map((group, i) => {
        const titleLink = group.querySelector(".chatlog__title-replacement");
        const title = normalizeInlineWhitespace(
          titleLink ? (titleLink.textContent || "") : (group.dataset.reportTitle || `Entry ${i + 1}`)
        );
        const href = titleLink
          ? (titleLink.getAttribute("href") || "")
          : (group.id ? `#${group.id}` : "");
        const summary = group.dataset.summary || "";
        return { title, href, summary };
      })
      .filter(item => item.title && item.href.startsWith("#"));

    if (reportItems.length) {
      const tocBlock = document.createElement("div");
      tocBlock.className = "toc-block";

      const tocTitle = document.createElement("div");
      tocTitle.className = "toc-title";
      tocTitle.textContent = "Table of Contents";

      const tocList = document.createElement("div");
      tocList.className = "toc-list";

      reportItems.forEach(item => {
        const entry = document.createElement("div");
        entry.className = "toc-item";

        const a = document.createElement("a");
        a.className = "toc-item-title";
        a.href = item.href;
        a.textContent = item.title;

        const summary = document.createElement("div");
        summary.className = "toc-item-summary";
        summary.textContent = item.summary;

        entry.appendChild(a);
        entry.appendChild(summary);
        tocList.appendChild(entry);
      });

      tocBlock.appendChild(tocTitle);
      tocBlock.appendChild(tocList);

      const entriesContainer = preamble.querySelector(".preamble__entries-container");
      const btcNote = preamble.querySelector(".btc-note");

      if (btcNote) {
        btcNote.insertAdjacentElement("beforebegin", tocBlock);
      } else if (entriesContainer) {
        entriesContainer.appendChild(tocBlock);
      } else {
        preamble.appendChild(tocBlock);
      }
    }
  }

  if (document.title) {
    document.title = document.title.replace(
      /^(Veilocity\s*-\s*)(.+)$/i,
      (_, _prefix, country) => "Report - " + capitalizeWords(country.trim())
    );
  }

  document.querySelectorAll(".chatlog__message-group").forEach(group => {
    let existingReturn = group.querySelector(".post-return-wrap");
    if (existingReturn) existingReturn.remove();

    const wrap = document.createElement("div");
    wrap.className = "post-return-wrap";

    const link = document.createElement("a");
    link.className = "post-return-link";
    link.href = "#top";
    link.textContent = "Return to top";

    wrap.appendChild(link);
    group.appendChild(wrap);
  });
});
</script>
""".strip()


def capitalize_words(text: str) -> str:
    return re.sub(
        r'\b([A-Za-z\u00C0-\u024F\u0400-\u04FF])([A-Za-z\u00C0-\u024F\u0400-\u04FF]*)\b',
        lambda m: m.group(1).upper() + m.group(2).lower(),
        text
    )


def capitalize_channel_title(html: str) -> str:
    match = re.search(r'(<title[^>]*>)(.*?)(</title>)', html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return html

    opening, title_text, closing = match.groups()
    title_clean = unescape(title_text).strip()

    prefix_match = re.match(r'^(Veilocity\s*-\s*)(.+)$', title_clean, flags=re.IGNORECASE)
    if not prefix_match:
        return html

    prefix = "Report - "
    country = prefix_match.group(2).strip()
    if not country:
        return html

    fixed_title = f"{prefix}{capitalize_words(country)}"
    return html[:match.start()] + opening + fixed_title + closing + html[match.end():]


def remove_previous_flag_markup(html: str) -> str:
    return re.sub(
        r'\sdata-flag-src="[^"]*"',
        '',
        html,
        flags=re.IGNORECASE
    )


def set_body_flag_src(html: str, flag_filename: str | None) -> str:
    html = remove_previous_flag_markup(html)

    if not flag_filename:
        return html

    body_match = re.search(r'<body\b([^>]*)>', html, flags=re.IGNORECASE | re.DOTALL)
    if not body_match:
        return html

    body_tag = body_match.group(0)
    attrs = body_match.group(1)

    if re.search(r'\bdata-flag-src\s*=', attrs, flags=re.IGNORECASE):
        new_body_tag = re.sub(
            r'\bdata-flag-src\s*=\s*"[^"]*"',
            f'data-flag-src="{flag_filename}"',
            body_tag,
            flags=re.IGNORECASE
        )
    else:
        new_body_tag = body_tag[:-1] + f' data-flag-src="{flag_filename}">'

    return html[:body_match.start()] + new_body_tag + html[body_match.end():]


def find_runtime_flag(script_dir: Path) -> Path | None:
    pngs = sorted(p for p in script_dir.glob("*.png") if p.is_file())
    if not pngs:
        return None
    return pngs[0]


def copy_flag_to_directory(source_flag: Path | None, dest_dir: Path) -> str | None:
    if source_flag is None:
        return None

    source_flag = source_flag.resolve()
    dest_dir = dest_dir.resolve()

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = (dest_dir / source_flag.name).resolve()

    if source_flag == dest_path:
        print(f"Flag already in target directory: {dest_path.name}")
        return dest_path.name

    shutil.copy2(source_flag, dest_path)
    print(f"Copied flag: {source_flag.name} -> {dest_path}")
    return dest_path.name


def inject_into_file(file_path: Path, flag_filename: str | None = None):
    if not file_path.is_file():
        print(f"Skipping non-file: {file_path}")
        return

    if file_path.suffix.lower() != ".html":
        print(f"Skipping non-html: {file_path}")
        return

    original_html = file_path.read_text(encoding="utf-8", errors="replace")
    html = capitalize_channel_title(original_html)
    html = set_body_flag_src(html, flag_filename)
    lower_html = html.lower()

    backup_path = file_path.with_name(file_path.name + ".bak")
    backup_path.write_text(original_html, encoding="utf-8")

    start_marker = '<script id="report-chatlog-enhancer">'
    end_marker = '</script>'

    start = lower_html.find(start_marker.lower())
    if start != -1:
      end = lower_html.find(end_marker.lower(), start)
      if end != -1:
          end += len(end_marker)
          html = html[:start] + html[end:]
          lower_html = html.lower()

    insert_at = lower_html.rfind("</body>")
    if insert_at != -1:
        new_html = html[:insert_at] + "\n" + INJECTION + "\n" + html[insert_at:]
    else:
        insert_at = lower_html.rfind("</html>")
        if insert_at != -1:
            new_html = html[:insert_at] + "\n" + INJECTION + "\n" + html[insert_at:]
        else:
            new_html = html + "\n" + INJECTION + "\n"

    file_path.write_text(new_html, encoding="utf-8")

    print(f"Updated: {file_path}")
    print(f"Backup:  {backup_path}")
    if flag_filename:
        print(f"Flag:    {flag_filename}")


def process_path(path: Path, flag_filename: str | None = None):
    if path.is_dir():
        html_files = sorted(path.glob("*.html"))
        if not html_files:
            print(f"No .html files found in directory: {path}")
            return
        for file_path in html_files:
            inject_into_file(file_path, flag_filename=flag_filename)
    else:
        inject_into_file(path, flag_filename=flag_filename)


def main():
    script_dir = Path(__file__).resolve().parent
    args = sys.argv[1:]

    if not args:
        html_dir = Path(".")
        html_files = sorted(html_dir.glob("*.html"))
        if not html_files:
            print("No .html files found in current directory.")
            sys.exit(1)

        runtime_flag = find_runtime_flag(script_dir)
        flag_filename = copy_flag_to_directory(runtime_flag, html_dir)

        if runtime_flag:
            print(f"Using flag: {runtime_flag.name}")
        else:
            print("No runtime .png flag found beside the script. Continuing without a flag.")

        for file_path in html_files:
            inject_into_file(file_path, flag_filename=flag_filename)
        return

    candidate = Path(" ".join(args))
    if candidate.exists():
        target_dir = candidate if candidate.is_dir() else candidate.parent
        runtime_flag = find_runtime_flag(script_dir)
        flag_filename = copy_flag_to_directory(runtime_flag, target_dir)

        if runtime_flag:
            print(f"Using flag: {runtime_flag.name}")
        else:
            print("No runtime .png flag found beside the script. Continuing without a flag.")

        process_path(candidate, flag_filename=flag_filename)
        return

    runtime_flag = find_runtime_flag(script_dir)

    for arg in args:
        target = Path(arg)
        target_dir = target if target.is_dir() else target.parent
        flag_filename = copy_flag_to_directory(runtime_flag, target_dir)

        if runtime_flag:
            print(f"Using flag for {target}: {runtime_flag.name}")
        else:
            print(f"No runtime .png flag found beside the script for {target}. Continuing without a flag.")

        process_path(target, flag_filename=flag_filename)


if __name__ == "__main__":
    main()
