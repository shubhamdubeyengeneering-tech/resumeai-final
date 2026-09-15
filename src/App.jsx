import { useEffect, useRef, useState } from "react";
import "./App.css";

const API_URL =
  import.meta.env.VITE_API_URL ||
  (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://127.0.0.1:8000"
    : "https://resumeai-docker.onrender.com");


// Lightweight whole-workspace UI translation. User-generated content and AI output are
// intentionally not translated here; the AI/Mock language controls handle those.
const UI_TRANSLATIONS = {
  "Choose Your Resume Style": "अपना रिज्यूमे स्टाइल चुनें",
  "Pick a design first. The selected version can then be downloaded as a PDF.": "पहले डिजाइन चुनें। चुना गया वर्जन PDF के रूप में डाउनलोड किया जा सकता है।",
  "Professional": "प्रोफेशनल",
  "Executive Two-Column": "एग्जीक्यूटिव टू-कॉलम",
  "Modern Sidebar": "मॉडर्न साइडबार",
  "Minimal ATS": "मिनिमल ATS",
  "Existing ResumeAI Style": "मौजूदा ResumeAI स्टाइल",
  "Inspired by your sample": "आपके सैंपल से प्रेरित",
  "Bold & structured": "बोल्ड और स्ट्रक्चर्ड",
  "Clean & recruiter-friendly": "क्लीन और रिक्रूटर-फ्रेंडली",
  "Selected": "चुना गया",
  "Select": "चुनें",
  "Preview:": "प्रीव्यू:",
  "Preparing PDF...": "PDF तैयार हो रही है...",
  "⬇ Download Selected PDF": "⬇ चुना गया PDF डाउनलोड करें",
  "Dashboard": "डैशबोर्ड", "Mocks": "मॉक इंटरव्यू", "Jobs": "जॉब्स", "Resources": "संसाधन", "Analytics": "विश्लेषण",
  "Resume Analyzer": "रिज्यूमे विश्लेषक", "My Applications": "मेरे आवेदन", "Profile": "प्रोफ़ाइल", "Settings": "सेटिंग्स",
  "Login / Sign Up": "लॉगिन / साइन अप", "My Profile": "मेरी प्रोफ़ाइल", "Logout": "लॉगआउट", "Login": "लॉगिन", "Create Account": "अकाउंट बनाएं",
  "WORKSPACE": "वर्कस्पेस", "AI Career Intelligence": "एआई करियर इंटेलिजेंस", "AI + Human": "एआई + मानव",
  "Build Better Resumes.": "बेहतर रिज्यूमे बनाएं।", "Get Better Jobs.": "बेहतर जॉब पाएं।",
  "AI Mock Interviews": "एआई मॉक इंटरव्यू", "Practice like it is a real interview.": "ऐसे अभ्यास करें जैसे यह असली इंटरव्यू हो।",
  "Target role": "लक्षित भूमिका", "Target goal": "लक्षित लक्ष्य", "Interview language": "इंटरव्यू की भाषा", "Interview mode": "इंटरव्यू मोड",
  "Start 10-Question Interview →": "10 प्रश्नों का इंटरव्यू शुरू करें →", "End Interview": "इंटरव्यू समाप्त करें",
  "Send Answer →": "उत्तर भेजें →", "Next AI Question →": "अगला एआई प्रश्न →", "Start New Interview →": "नया इंटरव्यू शुरू करें →",
  "English": "अंग्रेज़ी", "Hindi": "हिंदी", "Hinglish": "हिंग्लिश",
  "Jobs": "जॉब्स", "Find jobs that fit your resume": "अपने रिज्यूमे के अनुसार जॉब खोजें", "Search Jobs": "जॉब खोजें",
  "Search role, skill or keyword": "भूमिका, स्किल या कीवर्ड खोजें", "Smart job filters": "स्मार्ट जॉब फ़िल्टर", "Apply Filters": "फ़िल्टर लगाएं", "Clear": "साफ़ करें",
  "Profile": "प्रोफ़ाइल", "Edit Profile": "प्रोफ़ाइल संपादित करें", "Cancel Edit": "एडिट रद्द करें", "Save Profile →": "प्रोफ़ाइल सेव करें →",
  "Full Name": "पूरा नाम", "Email Address": "ईमेल पता", "Phone Number": "फ़ोन नंबर", "Location": "स्थान", "Professional Headline": "प्रोफ़ेशनल हेडलाइन",
  "Professional Summary": "प्रोफ़ेशनल सारांश", "Skills & Technologies": "स्किल्स और टेक्नोलॉजी",
  "Settings": "सेटिंग्स", "CONTROL CENTER": "कंट्रोल सेंटर", "Account": "अकाउंट", "Appearance": "दिखावट", "Notifications": "सूचनाएं",
  "Resume Preferences": "रिज्यूमे प्राथमिकताएं", "AI Preferences": "एआई प्राथमिकताएं", "Security": "सुरक्षा",
  "Personal details and account information": "व्यक्तिगत और अकाउंट जानकारी", "Theme and display preferences": "थीम और डिस्प्ले सेटिंग्स",
  "Email and weekly updates": "ईमेल और साप्ताहिक अपडेट", "Resume upload and analysis": "रिज्यूमे अपलोड और विश्लेषण",
  "AI assistant and suggestions": "एआई असिस्टेंट और सुझाव", "Password and session management": "पासवर्ड और सेशन प्रबंधन",
  "Light": "लाइट", "Dark": "डार्क", "Clean bright workspace": "साफ़ और उजला वर्कस्पेस", "Low-light focused workspace": "कम रोशनी के लिए आरामदायक वर्कस्पेस",
  "Choose how ResumeAI looks on your device.": "अपने डिवाइस पर ResumeAI की दिखावट चुनें।", "Theme changes apply immediately.": "थीम तुरंत लागू होती है।",
  "Your identity and account information.": "आपकी पहचान और अकाउंट की जानकारी।", "Open Full Profile →": "पूरी प्रोफ़ाइल खोलें →", "Workspace active": "वर्कस्पेस सक्रिय है",
  "AI response language": "वेबसाइट की भाषा", "Career Chat understands English, Hindi and Hinglish.": "पूरी वेबसाइट की भाषा यहां चुनें।",
  "Website language": "वेबसाइट की भाषा", "Change the language of the ResumeAI interface.": "ResumeAI इंटरफेस की भाषा बदलें।",
  "Notifications": "सूचनाएं", "Mark all read": "सभी को पढ़ा हुआ करें", "No notifications yet.": "अभी कोई सूचना नहीं है।",
  "Profile photo": "प्रोफ़ाइल फोटो", "Change Photo": "फोटो बदलें", "Remove Photo": "फोटो हटाएं",
  "Coming Soon": "जल्द आ रहा है", "Premium": "प्रीमियम", "ResumeAI Premium": "ResumeAI प्रीमियम",
  "What we are building next.": "हम आगे क्या बना रहे हैं।", "🚀 Coming Soon": "🚀 जल्द आ रहा है",
};
Object.assign(UI_TRANSLATIONS, {
  "AI Career Matching": "एआई करियर मैचिंग", "Career Intelligence": "करियर इंटेलिजेंस", "Career readiness": "करियर तैयारी",
  "Career Tracker": "करियर ट्रैकर", "Live account data": "लाइव अकाउंट डेटा", "Application timeline": "आवेदन टाइमलाइन",
  "Overall Score": "कुल स्कोर", "Match Potential": "मैच संभावना", "Strong Points": "मजबूत पक्ष", "Areas to Improve": "सुधार के क्षेत्र",
  "Next Steps": "अगले कदम", "Quick Tip": "त्वरित सुझाव", "Keep going! ↗": "आगे बढ़ते रहें! ↗",
  "Your Resume Journey Starts Here": "आपकी रिज्यूमे यात्रा यहां से शुरू होती है", "Great Resume!": "बेहतरीन रिज्यूमे!", "Good Start!": "अच्छी शुरुआत!", "Let's Improve It!": "इसे और बेहतर बनाएं!",
  "Needs work": "सुधार की जरूरत", "Job ready": "जॉब के लिए तैयार", "Job Ready.": "जॉब के लिए तैयार।",
  "Analyze first": "पहले विश्लेषण करें", "Analyze a resume to generate personalized next steps.": "व्यक्तिगत अगले कदम पाने के लिए रिज्यूमे का विश्लेषण करें।",
  "Review your resume score and section feedback.": "अपने रिज्यूमे स्कोर और सेक्शन फीडबैक की समीक्षा करें।",
  "Use AI Career Advisor for career guidance.": "करियर मार्गदर्शन के लिए एआई करियर सलाहकार का उपयोग करें।",
  "Your score reflects resume structure, content quality, evidence and ATS-related factors detected in the uploaded resume.": "आपका स्कोर अपलोड किए गए रिज्यूमे में मिली संरचना, कंटेंट गुणवत्ता, प्रमाण और ATS से जुड़े कारकों पर आधारित है।",
  "View Full Report →": "पूरी रिपोर्ट देखें →", "Why this score?": "यह स्कोर क्यों?", "Hide Score Details ↑": "स्कोर विवरण छिपाएं ↑", "View Score Details ↓": "स्कोर विवरण देखें ↓",
  "Find jobs that fit your resume": "अपने रिज्यूमे के अनुसार जॉब खोजें", "Resume-based matching is ON. Filters below are generated from your analyzed resume.": "रिज्यूमे आधारित मैचिंग चालू है। नीचे के फ़िल्टर आपके विश्लेषित रिज्यूमे से बनाए गए हैं।",
  "Analyze a resume first to unlock resume-based matching and personalized filters.": "रिज्यूमे आधारित मैचिंग और व्यक्तिगत फ़िल्टर के लिए पहले रिज्यूमे का विश्लेषण करें।",
  "Search Jobs": "जॉब खोजें", "Searching...": "खोज रहे हैं...", "No matching jobs": "कोई मैचिंग जॉब नहीं", "Try another role, skill or filter.": "दूसरी भूमिका, स्किल या फ़िल्टर आज़माएं।",
  "View Job →": "जॉब देखें →", "Open Job Posting ↗": "जॉब पोस्टिंग खोलें ↗", "All matching roles": "सभी मैचिंग भूमिकाएं", "Any country": "कोई भी देश", "Any experience": "कोई भी अनुभव", "Any location": "कोई भी स्थान", "Any resume skill": "कोई भी रिज्यूमे स्किल",
  "Smart job filters": "स्मार्ट जॉब फ़िल्टर", "Role, skill, country, work mode and experience.": "भूमिका, स्किल, देश, काम का तरीका और अनुभव।",
  "My Applications": "मेरे आवेदन", "Application tracker": "आवेदन ट्रैकर", "Your application tracker is ready": "आपका आवेदन ट्रैकर तैयार है",
  "One clean place to manage every opportunity and see your progress.": "हर अवसर को संभालने और अपनी प्रगति देखने की एक साफ जगह।", "Add an opportunity": "एक अवसर जोड़ें", "Add your first opportunity and start building your career pipeline.": "अपना पहला अवसर जोड़ें और अपना करियर पाइपलाइन बनाना शुरू करें।",
  "Company": "कंपनी", "Role": "भूमिका", "Status": "स्थिति", "Job URL": "जॉब URL", "Notes": "नोट्स", "Offer": "ऑफर", "Rejected": "अस्वीकृत", "Withdrawn": "वापस लिया गया", "Applied": "आवेदन किया",
  "Profile": "प्रोफ़ाइल", "Professional profile": "प्रोफ़ेशनल प्रोफ़ाइल", "Edit the details ResumeAI uses across your career workspace.": "वे विवरण संपादित करें जिन्हें ResumeAI आपके करियर वर्कस्पेस में उपयोग करता है।",
  "Career Identity": "करियर पहचान", "Location not added": "स्थान नहीं जोड़ा गया", "Add a professional headline to make your profile stronger.": "प्रोफ़ाइल को मजबूत बनाने के लिए प्रोफ़ेशनल हेडलाइन जोड़ें।",
  "Career goal": "करियर लक्ष्य", "Skills listed": "सूचीबद्ध स्किल्स", "Professional profile": "प्रोफ़ेशनल प्रोफ़ाइल",
  "Settings": "सेटिंग्स", "Every control below is interactive and saves to your ResumeAI workspace.": "नीचे का हर कंट्रोल इंटरैक्टिव है और आपके ResumeAI वर्कस्पेस में सेव होता है।",
  "Account": "अकाउंट", "Personal details and account information": "व्यक्तिगत विवरण और अकाउंट जानकारी", "Appearance": "दिखावट", "Theme and display preferences": "थीम और डिस्प्ले प्राथमिकताएं",
  "Notifications": "सूचनाएं", "Email and weekly updates": "ईमेल और साप्ताहिक अपडेट", "Resume Preferences": "रिज्यूमे प्राथमिकताएं", "Resume upload and analysis": "रिज्यूमे अपलोड और विश्लेषण",
  "AI Preferences": "एआई प्राथमिकताएं", "AI assistant and suggestions": "एआई असिस्टेंट और सुझाव", "Security": "सुरक्षा", "Password and session management": "पासवर्ड और सेशन प्रबंधन",
  "Website language": "वेबसाइट की भाषा", "Change the language of the ResumeAI interface.": "ResumeAI इंटरफेस की भाषा बदलें।", "Choose how ResumeAI looks on your device.": "अपने डिवाइस पर ResumeAI की दिखावट चुनें।",
  "Clean bright workspace": "साफ़ उजला वर्कस्पेस", "Low-light focused workspace": "कम रोशनी के लिए आरामदायक वर्कस्पेस", "Theme changes apply immediately.": "थीम तुरंत लागू होती है।",
  "Light": "लाइट", "Dark": "डार्क", "English": "अंग्रेज़ी", "Hindi": "हिंदी",
  "Email notifications": "ईमेल सूचनाएं", "Weekly career summary": "साप्ताहिक करियर सारांश", "Important account and feature updates.": "महत्वपूर्ण अकाउंट और फीचर अपडेट।",
  "AI Interview Voice": "एआई इंटरव्यू आवाज़", "Choose whether the AI interviewer speaks and which voice style it uses.": "चुनें कि एआई इंटरव्यूअर बोले या नहीं और कौन-सी आवाज़ शैली इस्तेमाल करे।",
  "Female voice": "महिला आवाज़", "Male voice": "पुरुष आवाज़", "Test Voice": "आवाज़ जांचें", "Resume-grounded feedback": "रिज्यूमे-आधारित फीडबैक", "Adaptive mock interviews": "अनुकूली मॉक इंटरव्यू", "Multilingual chat": "बहुभाषी चैट", "Evidence-aware suggestions": "प्रमाण-आधारित सुझाव",
  "Security PIN": "सुरक्षा PIN", "Website Lock": "वेबसाइट लॉक", "Enable Lock": "लॉक चालू करें", "Disable Lock": "लॉक बंद करें", "Turn Off Lock": "लॉक बंद करें", "Change PIN": "PIN बदलें", "Remove PIN": "PIN हटाएं", "Create Website PIN": "वेबसाइट PIN बनाएं",
  "Create a 4-12 digit PIN": "4-12 अंकों का PIN बनाएं", "Confirm PIN": "PIN की पुष्टि करें", "Current PIN": "वर्तमान PIN", "New PIN": "नया PIN", "Confirm New PIN": "नए PIN की पुष्टि करें",
  "Your PIN is never displayed or included in normal settings auto-save.": "आपका PIN कभी दिखाया नहीं जाता और सामान्य सेटिंग्स ऑटो-सेव में शामिल नहीं होता।",
  "Resume Analysis": "रिज्यूमे विश्लेषण", "Resume analysis": "रिज्यूमे विश्लेषण", "Supported formats": "समर्थित फॉर्मेट", "PHOTO": "फोटो",
  "Mock interview complete.": "मॉक इंटरव्यू पूरा हुआ।", "Start New Interview →": "नया इंटरव्यू शुरू करें →", "View Career Analytics": "करियर एनालिटिक्स देखें",
  "Your answer": "आपका उत्तर", "Speak or type naturally. The AI evaluates what you actually say.": "स्वाभाविक रूप से बोलें या टाइप करें। एआई आपके वास्तविक उत्तर का मूल्यांकन करता है।",
  "AI Interviewer": "एआई इंटरव्यूअर", "QUESTION": "प्रश्न", "OF": "में से", "Send Answer →": "उत्तर भेजें →", "End Interview": "इंटरव्यू समाप्त करें",
  "Start 10-Question Interview →": "10 प्रश्नों का इंटरव्यू शुरू करें →", "Practice like it is a real interview.": "ऐसे अभ्यास करें जैसे यह असली इंटरव्यू हो।",
  "Target role": "लक्षित भूमिका", "Target goal": "लक्षित लक्ष्य", "Interview language": "इंटरव्यू की भाषा", "Interview mode": "इंटरव्यू मोड",
  "AI + Human Text": "एआई + मानव टेक्स्ट", "AI Voice + Human Voice": "एआई आवाज़ + मानव आवाज़", "Preparing AI Interview...": "एआई इंटरव्यू तैयार हो रहा है...",
  "RESUMEAI AI INTERVIEWER": "RESUMEAI एआई इंटरव्यूअर", "LIVE AI INTERVIEW": "लाइव एआई इंटरव्यू", "AI asks in chat. Type your answer below, or switch to Voice AI for spoken practice.": "एआई चैट में पूछता है। नीचे अपना उत्तर टाइप करें या बोलकर अभ्यास के लिए Voice AI चुनें।",
  "AI asks by voice. You can answer by voice or type your answer below.": "एआई आवाज़ में पूछता है। आप आवाज़ से या नीचे टाइप करके उत्तर दे सकते हैं।",
  "ResumeAI Premium": "ResumeAI प्रीमियम", "Coming Soon": "जल्द आ रहा है", "Advanced career tools and future premium features.": "उन्नत करियर टूल्स और भविष्य के प्रीमियम फीचर्स।",
  "No notifications yet.": "अभी कोई सूचना नहीं है।", "Mark all read": "सभी को पढ़ा हुआ करें", "Open Full Profile →": "पूरी प्रोफ़ाइल खोलें →",
});
const UI_TRANSLATIONS_REVERSE = Object.fromEntries(Object.entries(UI_TRANSLATIONS).map(([en, hi]) => [hi, en]));
function translateUiText(value, language) {
  if (language !== "Hindi") return UI_TRANSLATIONS_REVERSE[value] || value;
  return UI_TRANSLATIONS[value] || value;
}
const UI_ORIGINAL_TEXT = new WeakMap();
const UI_ORIGINAL_ATTRS = new WeakMap();

// Keep the English source text separately from whatever is currently rendered.
// React can reuse an existing text node when navigating between pages. If that
// happens, the node may be changed from Hindi back to English while its WeakMap
// entry still contains the old Hindi value. Track the last value we rendered so
// navigation is translated again correctly.
function installUiLanguageObserver(language) {
  const root = document.body;
  if (!root) return () => {};

  const update = () => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);

    nodes.forEach(node => {
      const parent = node.parentElement;
      if (!parent || ["SCRIPT", "STYLE", "NOSCRIPT"].includes(parent.tagName)) return;

      const raw = node.nodeValue || "";
      const trimmed = raw.trim();
      if (!trimmed || trimmed.length > 180) return;

      let record = UI_ORIGINAL_TEXT.get(node);
      if (!record) {
        record = { original: trimmed, lastRendered: trimmed };
        UI_ORIGINAL_TEXT.set(node, record);
      } else if (trimmed !== record.lastRendered) {
        // React/navigation changed this node. The new value is the fresh English
        // source unless it is already one of our known translations.
        const knownHindi = UI_TRANSLATIONS[trimmed];
        const knownEnglish = UI_TRANSLATIONS_REVERSE[trimmed];
        if (knownEnglish) {
          record.original = knownEnglish;
        } else if (!knownHindi) {
          record.original = trimmed;
        }
      }

      const translated = translateUiText(record.original, language);
      if (translated !== trimmed) {
        node.nodeValue = raw.replace(trimmed, translated);
      }
      record.lastRendered = translated;
    });

    root.querySelectorAll("input[placeholder], textarea[placeholder], [aria-label], [title]").forEach(el => {
      let record = UI_ORIGINAL_ATTRS.get(el);
      if (!record) {
        record = {
          placeholder: el.getAttribute("placeholder"),
          aria: el.getAttribute("aria-label"),
          title: el.getAttribute("title"),
          lastPlaceholder: el.getAttribute("placeholder"),
          lastAria: el.getAttribute("aria-label"),
          lastTitle: el.getAttribute("title"),
        };
        UI_ORIGINAL_ATTRS.set(el, record);
      }

      const syncAttr = (name, lastName) => {
        const current = el.getAttribute(name);
        const last = record[lastName];
        if (current !== last) {
          const knownEnglish = current ? UI_TRANSLATIONS_REVERSE[current] : null;
          if (knownEnglish) record[name] = knownEnglish;
          else if (current && !UI_TRANSLATIONS[current]) record[name] = current;
        }
        const original = record[name];
        if (original) el.setAttribute(name, translateUiText(original, language));
        else if (current === null) el.removeAttribute(name);
        record[lastName] = el.getAttribute(name);
      };

      syncAttr("placeholder", "lastPlaceholder");
      syncAttr("aria-label", "lastAria");
      syncAttr("title", "lastTitle");
    });
  };

  // Disconnect while changing DOM so our own translations can never trigger an
  // endless MutationObserver loop. Re-observe after the update for React route
  // changes and newly mounted page content.
  let applying = false;
  let observer = null;
  const safeUpdate = () => {
    if (applying) return;
    applying = true;
    if (observer) observer.disconnect();
    try {
      update();
    } finally {
      applying = false;
      if (observer) {
        observer.observe(root, {
          childList: true,
          subtree: true,
          characterData: true,
          attributes: true,
          attributeFilter: ["placeholder", "aria-label", "title"],
        });
      }
    }
  };

  observer = new MutationObserver(() => safeUpdate());
  safeUpdate();
  return () => observer && observer.disconnect();
}

function getGuestId() {
  try {
    let id = localStorage.getItem("resumeai_guest_id");
    if (!id) {
      id = typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `guest-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      localStorage.setItem("resumeai_guest_id", id);
    }
    return id;
  } catch {
    return "guest-browser";
  }
}

function apiAuthHeaders() {
  const token = localStorage.getItem("resumeai_token");
  return token
    ? { Authorization: `Bearer ${token}` }
    : { "X-Guest-ID": getGuestId() };
}

const SECTION_LIST = [
  ["contact", "Contact"],
  ["summary", "Summary"],
  ["education", "Education"],
  ["skills", "Skills"],
  ["experience", "Experience"],
  ["internship", "Internship"],
  ["projects", "Projects"],
  ["certifications", "Certifications"],
  ["achievements", "Achievements"],
];

function getScoreInfo(score) {
  if (score >= 90) {
    return {
      className: "good",
      label: "Excellent Resume",
      emoji: "🏆",
      message:
        "Your resume is already strong. Focus on small improvements to make it even more competitive.",
    };
  }

  if (score >= 80) {
    return {
      className: "good",
      label: "Strong Resume",
      emoji: "🌟",
      message:
        "Your resume has a strong foundation with a few areas that can still be improved.",
    };
  }

  if (score >= 70) {
    return {
      className: "average",
      label: "Good Resume",
      emoji: "👍",
      message:
        "Your resume is good, but improving content quality and evidence can make it significantly stronger.",
    };
  }

  if (score >= 60) {
    return {
      className: "average",
      label: "Needs Improvement",
      emoji: "⚠️",
      message:
        "Your resume needs some important improvements before it is fully job-ready.",
    };
  }

  return {
    className: "poor",
    label: "Weak Resume",
    emoji: "🛠️",
    message:
      "Your resume currently has several important gaps. Focus on the highest-priority improvements first.",
  };
}

function canonicalSections(sections) {
  if (!Array.isArray(sections)) return [];

  return sections.map((item) =>
    String(item).toLowerCase()
  );
}

function isSectionHeading(line) {
  const value = line
    .replace(/[^a-zA-Z ]/g, "")
    .trim()
    .toLowerCase();

  const headings = [
    "professional summary",
    "summary",
    "profile",
    "objective",
    "skills",
    "technical skills",
    "experience",
    "work experience",
    "professional experience",
    "internship",
    "internships",
    "projects",
    "education",
    "certifications",
    "certification",
    "achievements",
    "awards",
    "honors",
  ];

  return headings.includes(value);
}

function isBullet(line) {
  return /^(?:[•●▪◦‣*-]|\d+[.)])\s+/.test(
    line.trim()
  );
}

function renderEnhancedPreview(text, photoDataUrl = "", template = "professional") {
  if (!text) return null;

  const lines = text.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
  const sectionNames = new Set([
    "summary", "professional summary", "objective", "profile", "skills", "technical skills",
    "experience", "work experience", "professional experience", "education", "projects",
    "certifications", "achievements", "awards", "languages", "interests", "internship", "internships"
  ]);

  let name = lines[0] || "Your Name";
  let contact = "";
  let currentSection = "";
  const sections = [];
  const sectionMap = new Map();

  lines.slice(1).forEach(line => {
    const normalized = line.replace(/[:]/g, "").toLowerCase();
    if (!contact && (line.includes("@") || /linkedin|github|\+?\d[\d\s().-]{7,}/i.test(line))) {
      contact = line;
      return;
    }
    if (sectionNames.has(normalized)) {
      currentSection = line;
      const item = { title: line, items: [] };
      sections.push(item);
      sectionMap.set(normalized, item);
      return;
    }
    if (!currentSection) {
      currentSection = "Professional Summary";
      let item = sectionMap.get("professional summary");
      if (!item) { item = { title: "Professional Summary", items: [] }; sections.push(item); sectionMap.set("professional summary", item); }
      item.items.push(line);
      return;
    }
    const item = sectionMap.get(currentSection.replace(/[:]/g, "").toLowerCase());
    if (item) item.items.push(line); else sections.push({ title: currentSection, items: [line] });
  });

  const leftTitles = new Set(["skills", "technical skills", "languages", "certifications", "achievements", "awards", "interests"]);
  const left = sections.filter(s => leftTitles.has(s.title.replace(/[:]/g, "").toLowerCase()));
  const right = sections.filter(s => !leftTitles.has(s.title.replace(/[:]/g, "").toLowerCase()));

  const Section = ({ section }) => (
    <section className="enhanced-preview-section">
      <h4>{section.title.toUpperCase()}</h4>
      {section.items.map((item, i) => {
        const bullet = isBullet(item);
        return bullet ? <div className="enhanced-preview-bullet" key={i}><span>•</span><span>{item.replace(/^(?:[•●▪◦‣*-]|\d+[.)])\s+/, "")}</span></div> : <p key={i}>{item}</p>;
      })}
    </section>
  );

  return (
    <div className={`enhanced-preview-paper enhanced-template-${template}`}>
      <header className="enhanced-preview-header">
        <div>
          <h2>{name}</h2>
          <div className="enhanced-preview-contact">{contact || "Professional Profile"}</div>
        </div>
        {photoDataUrl ? <img src={photoDataUrl} alt="Profile" className="enhanced-preview-photo" /> : <div className="enhanced-preview-photo-placeholder">PHOTO</div>}
      </header>
      <div className="enhanced-preview-columns">
        <aside>{left.length ? left.map((section, i) => <Section section={section} key={i} />) : <Section section={{title:"Key Skills", items:["Skills from your original resume are preserved in the generated PDF."]}} />}</aside>
        <div>{right.length ? right.map((section, i) => <Section section={section} key={i} />) : <Section section={{title:"Professional Summary", items:lines.slice(1)}} />}</div>
      </div>
    </div>
  );
}

function WorkspaceModules({ page, currentUser, onNavigate, resumeJobId, onLogout }) {
  const headers = apiAuthHeaders();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [mockRole, setMockRole] = useState("Software Engineer");
  const [mockTargetGoal, setMockTargetGoal] = useState("Get job-ready for this target role");
  const [mockSession, setMockSession] = useState(null);
  const [mockAnswer, setMockAnswer] = useState("");
  const [mockResult, setMockResult] = useState(null);
  const [mockNumber, setMockNumber] = useState(1);
  const [mockLanguage, setMockLanguage] = useState("English");
  const [mockListening, setMockListening] = useState(false);
  const [mockMode, setMockMode] = useState("text");
  const [aiSpeaking, setAiSpeaking] = useState(false);
  const [settingsTab, setSettingsTab] = useState("Account");
  const [security, setSecurity] = useState({ enabled: false, configured: false, mode: null, pin: "", confirmPin: "", currentPin: "", newPin: "", confirmNewPin: "" });
  const [jobs, setJobs] = useState([]);
  const [jobSearch, setJobSearch] = useState("");
  const [jobRoleFilter, setJobRoleFilter] = useState("");
  const [jobSkillFilter, setJobSkillFilter] = useState("");
  const [jobLocationFilter, setJobLocationFilter] = useState("");
  const [jobExperienceFilter, setJobExperienceFilter] = useState("Any experience");
  const [jobCountryFilter, setJobCountryFilter] = useState("Any country");
  const [jobWorkModeFilter, setJobWorkModeFilter] = useState("Any");
  const [jobFilterOptions, setJobFilterOptions] = useState({ roles: [], skills: [], locations: [], experience: [] });
  const [applications, setApplications] = useState([]);
  const [appForm, setAppForm] = useState({ company: "", role: "", location: "", url: "", status: "Applied", notes: "" });
  const [profile, setProfile] = useState({ name: currentUser?.name || "", email: currentUser?.email || "", phone: "", location: "", headline: "", bio: "", skills: "", photo: "" });
  const [profileEditing, setProfileEditing] = useState(false);
  const [settings, setSettings] = useState(() => ({ email_notifications: true, weekly_summary: true, language: "English", theme: (() => { try { const t = localStorage.getItem("resumeai_theme"); return t === "dark" ? "dark" : "light"; } catch { return "light"; } })(), voice_enabled: true, voice_gender: "female", lock_enabled: false, lock_pin: "" }));
  const [analytics, setAnalytics] = useState(null);
  const [premium, setPremium] = useState(null);
  const settingsHydratedRef = useRef(false);
  const settingsSaveTimerRef = useRef(null);

  async function api(path, options = {}) {
    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...headers, ...(options.headers || {}) },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || data.message || "Request failed.");
    return data;
  }

  useEffect(() => {
    // Guest mode is supported; account login is optional.
    if (!page) return;
    setMessage("");
    if (page === "applications") api("/api/applications").then(d => setApplications(d.applications || [])).catch(e => setMessage(e.message));
    else if (page === "profile") api("/api/profile").then(d => { setProfile(prev => ({...prev, ...(d.profile || {})})); setProfileEditing(false); }).catch(e => setMessage(e.message));
    else if (page === "settings") {
      settingsHydratedRef.current = false;
      Promise.all([api("/api/settings"), api("/api/security/status")]).then(([d, sec]) => {
        const incoming = d.settings || {};
        const safeTheme = incoming.theme === "dark" ? "dark" : "light";
        const safeLanguage = incoming.language === "Hindi" ? "Hindi" : "English";
        setSettings(prev => ({...prev, ...incoming, theme: safeTheme, language: safeLanguage}));
        setSecurity(prev => ({...prev, enabled: !!sec?.lock_enabled, configured: !!sec?.lock_configured, mode: null}));
        try { localStorage.setItem("resumeai_ui_language", safeLanguage); } catch {}
        window.setTimeout(() => { settingsHydratedRef.current = true; }, 0);
      }).catch(e => setMessage(e.message));
    }
    else if (page === "analytics") api("/api/analytics").then(d => setAnalytics(d.analytics)).catch(e => setMessage(e.message));
    else if (page === "premium") api("/api/premium/status").then(setPremium).catch(e => setPremium({ message: "Premium is currently being prepared." }));
    else if (page === "jobs") loadJobs(jobSearch);
    else if (page === "mocks") {
      // A new visit to Mocks must never auto-resume an old interview.
      // The user must explicitly press Start Interview.
      setMockSession(null); setMockResult(null); setMockAnswer(""); setMockNumber(1);
    }
  }, [page, currentUser]);

  useEffect(() => {
    const theme = settings.theme === "dark" ? "dark" : "light";
    document.documentElement.dataset.resumeaiTheme = theme;
    document.documentElement.classList.toggle("resumeai-dark", theme === "dark");
    document.documentElement.classList.remove("resumeai-neon");
    try { localStorage.setItem("resumeai_theme", theme); } catch {}
    window.dispatchEvent(new CustomEvent("resumeai-theme-updated", { detail: theme }));
  }, [settings.theme]);

  useEffect(() => {
    const lang = settings.language === "Hindi" ? "Hindi" : "English";
    try { localStorage.setItem("resumeai_ui_language", lang); } catch {}
    window.dispatchEvent(new CustomEvent("resumeai-language-updated", { detail: lang }));
  }, [settings.language]);

  // Settings are saved automatically after a short debounce. There is no manual save button.
  useEffect(() => {
    if (page !== "settings" || !settingsHydratedRef.current) return;
    window.clearTimeout(settingsSaveTimerRef.current);
    settingsSaveTimerRef.current = window.setTimeout(async () => {
      try {
        const { lock_enabled, lock_pin, lock_configured, ...generalSettings } = settings;
        await api("/api/settings", { method: "PUT", body: JSON.stringify(generalSettings) });
        setMessage("Settings saved automatically.");
      } catch (e) { setMessage(e.message); }
    }, 450);
    return () => window.clearTimeout(settingsSaveTimerRef.current);
  }, [settings, page]);

  function startVoiceInput() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setMessage("Voice input is not supported by this browser. You can still type your answer.");
      return;
    }
    if (mockListening) return;
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = mockLanguage === "English" ? "en-IN" : "hi-IN";
    recognition.onstart = () => setMockListening(true);
    recognition.onend = () => setMockListening(false);
    recognition.onerror = () => { setMockListening(false); setMessage("Voice input could not be captured. Please try again or type your answer."); };
    recognition.onresult = (event) => {
      const transcript = Array.from(event.results || []).map(r => r[0]?.transcript || "").join(" ").trim();
      if (transcript) setMockAnswer(prev => prev ? `${prev} ${transcript}` : transcript);
    };
    recognition.start();
  }

  function speakAIQuestion(text = mockSession?.question) {
    if (!text || !settings.voice_enabled || !window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      const voices = window.speechSynthesis.getVoices ? window.speechSynthesis.getVoices() : [];
      const wantedLang = mockLanguage === "Hindi" ? "hi-IN" : "en-IN";
      const wantedBase = wantedLang.slice(0, 2).toLowerCase();
      const gender = settings.voice_gender === "male" ? "male" : "female";
      const maleNames = ["ravi","david","guy","mark","alex","aaron","heera"];
      const femaleNames = ["zira","samantha","neerja","veena","susan","karen","hazel"];
      const preferredNames = gender === "male" ? maleNames : femaleNames;
      const matching = voices.filter(v => (v.lang || "").toLowerCase().startsWith(wantedBase));
      const ranked = [...matching].sort((a,b) => {
        const aName = (a.name || "").toLowerCase();
        const bName = (b.name || "").toLowerCase();
        const aGender = preferredNames.some(w => aName.includes(w)) ? 10 : 0;
        const bGender = preferredNames.some(w => bName.includes(w)) ? 10 : 0;
        const aPremium = /microsoft|google|apple/.test(aName) ? 2 : 0;
        const bPremium = /microsoft|google|apple/.test(bName) ? 2 : 0;
        return (bGender + bPremium) - (aGender + aPremium);
      });
      // Never attach an English voice to a Hindi interview. If no matching
      // Hindi voice is installed, let the browser choose using hi-IN instead.
      if (ranked[0]) utterance.voice = ranked[0];
      utterance.lang = wantedLang;
      utterance.rate = 0.9;
      utterance.pitch = gender === "male" ? 0.88 : 1.06;
      utterance.volume = 1;
      utterance.onstart = () => setAiSpeaking(true);
      utterance.onend = () => setAiSpeaking(false);
      utterance.onerror = () => setAiSpeaking(false);
      window.speechSynthesis.speak(utterance);
    } catch { setAiSpeaking(false); }
  }

  function previewVoice() {
    speakAIQuestion(mockLanguage === "Hindi" ? "Namaste! Yeh ResumeAI voice preview hai." : mockLanguage === "Hinglish" ? "Namaste! Yeh ResumeAI ka voice preview hai." : "Hello! This is the ResumeAI voice preview.");
  }

  useEffect(() => {
    if (page === "mocks" && mockSession?.question && mockMode === "voice" && settings.voice_enabled) {
      const timer = setTimeout(() => speakAIQuestion(mockSession.question), 250);
      return () => clearTimeout(timer);
    }
  }, [mockSession?.question, mockMode, settings.voice_enabled, settings.voice_gender, page]);

  useEffect(() => () => {
    try { window.speechSynthesis?.cancel(); } catch {}
  }, []);

  function goToResumeSection(id) {
    onNavigate("resume");
    window.setTimeout(() => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" }), 120);
  }

  async function loadJobs(search = jobSearch) {
    setBusy(true); setMessage("");
    try {
      const params = new URLSearchParams({
        search: search || "",
        resume_job_id: resumeJobId || "",
        role_filter: jobRoleFilter || "",
        skill_filter: jobSkillFilter || "",
        location_filter: jobLocationFilter || "",
        experience_filter: jobExperienceFilter || "Any experience",
        country: jobCountryFilter || "Any country",
        work_mode: jobWorkModeFilter || "Any",
        limit: "30",
      });
      const d = await api(`/api/jobs?${params.toString()}`);
      setJobs(d.jobs || []);
      setJobFilterOptions(d.filters || { roles: [], skills: [], locations: [], experience: [] });
    } catch (e) { setMessage(e.message); }
    finally { setBusy(false); }
  }

  async function startMock() {
    setBusy(true); setMessage(""); setMockResult(null); setMockAnswer(""); setMockNumber(1);
    try {
      const d = await api("/api/mocks/start", { method: "POST", body: JSON.stringify({ role: mockRole, target_goal: mockTargetGoal, language: mockLanguage, resume_job_id: resumeJobId || "" }) });
      setMockSession({ id: d.session_id, question: d.question, role: d.role, language: d.language });
    } catch (e) { setMessage(e.message); }
    finally { setBusy(false); }
  }

  async function submitMock() {
    if (!mockSession || !mockAnswer.trim()) return;
    setBusy(true); setMessage("");
    try {
      const d = await api(`/api/mocks/${mockSession.id}/answer`, { method: "POST", body: JSON.stringify({ answer: mockAnswer }) });
      setMockResult(d);
    } catch (e) { setMessage(e.message); }
    finally { setBusy(false); }
  }

  function nextMockQuestion() {
    if (!mockResult?.next_question) return;
    setMockSession(prev => prev ? { ...prev, question: mockResult.next_question } : prev);
    setMockNumber(mockResult.next_question_number || (mockNumber + 1));
    setMockResult(null);
    setMockAnswer("");
  }

  async function endMock() {
    if (!mockSession) return;
    try {
      await api(`/api/mocks/${mockSession.id}/cancel`, { method: "POST" });
    } catch (e) {
      setMessage(e.message);
      return;
    }
    try { window.speechSynthesis?.cancel(); } catch {}
    setMockSession(null);
    setMockResult(null);
    setMockAnswer("");
    setMockNumber(1);
    setMessage("Interview ended. Your completed answers remain saved.");
  }

  async function saveApplication(e) {
    e.preventDefault(); setBusy(true); setMessage("");
    try { const d = await api("/api/applications", { method: "POST", body: JSON.stringify(appForm) }); setApplications(prev => [d.application, ...prev]); setAppForm({ company: "", role: "", location: "", url: "", status: "Applied", notes: "" }); setMessage("Application added successfully."); }
    catch (e) { setMessage(e.message); }
    finally { setBusy(false); }
  }

  async function updateApplication(id, status) {
    try { const d = await api(`/api/applications/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }); setApplications(prev => prev.map(a => a.id === id ? d.application : a)); }
    catch (e) { setMessage(e.message); }
  }

  async function deleteApplication(id) {
    try { await api(`/api/applications/${id}`, { method: "DELETE" }); setApplications(prev => prev.filter(a => a.id !== id)); }
    catch (e) { setMessage(e.message); }
  }

  async function setupSecurityPin() {
    setMessage("");
    if (security.pin.length < 4 || security.pin.length > 12 || !/^\d+$/.test(security.pin)) { setMessage("PIN must contain 4-12 digits."); return; }
    if (security.pin !== security.confirmPin) { setMessage("PIN and confirmation do not match."); return; }
    setBusy(true);
    try {
      const d = await api("/api/security/set-pin", { method: "POST", body: JSON.stringify({ pin: security.pin, confirm_pin: security.confirmPin }) });
      setSecurity(prev => ({...prev, enabled: true, configured: true, mode: null, pin: "", confirmPin: ""}));
      setMessage(d.message || "PIN created successfully.");
    } catch (e) { setMessage(e.message); } finally { setBusy(false); }
  }

  async function changeSecurityPin() {
    setMessage("");
    if (security.newPin.length < 4 || !/^\d+$/.test(security.newPin)) { setMessage("New PIN must contain 4-12 digits."); return; }
    if (security.newPin !== security.confirmNewPin) { setMessage("New PIN and confirmation do not match."); return; }
    setBusy(true);
    try {
      const d = await api("/api/security/change-pin", { method: "POST", body: JSON.stringify({ current_pin: security.currentPin, new_pin: security.newPin, confirm_new_pin: security.confirmNewPin }) });
      setSecurity(prev => ({...prev, enabled: true, configured: true, mode: null, currentPin: "", newPin: "", confirmNewPin: ""}));
      setMessage(d.message || "PIN changed successfully.");
    } catch (e) { setMessage(e.message); } finally { setBusy(false); }
  }

  async function enableSecurityLock() {
    setMessage("");
    if (security.currentPin.length < 4) { setMessage("Enter your current PIN first."); return; }
    setBusy(true);
    try {
      const d = await api("/api/security/enable-lock", { method: "POST", body: JSON.stringify({ current_pin: security.currentPin }) });
      setSecurity(prev => ({...prev, enabled: true, configured: true, mode: null, currentPin: ""}));
      setMessage(d.message || "Website lock enabled.");
    } catch (e) { setMessage(e.message); } finally { setBusy(false); }
  }

  async function disableSecurityLock() {
    setMessage("");
    if (security.currentPin.length < 4) { setMessage("Enter your current PIN first."); return; }
    setBusy(true);
    try {
      const d = await api("/api/security/disable-lock", { method: "POST", body: JSON.stringify({ current_pin: security.currentPin }) });
      setSecurity(prev => ({...prev, enabled: false, configured: true, mode: null, currentPin: ""}));
      setMessage(d.message || "Website lock disabled.");
    } catch (e) { setMessage(e.message); } finally { setBusy(false); }
  }

  async function removeSecurityPin() {
    setMessage("");
    if (security.currentPin.length < 4) { setMessage("Enter your current PIN first."); return; }
    setBusy(true);
    try {
      const d = await api("/api/security/remove-pin", { method: "POST", body: JSON.stringify({ current_pin: security.currentPin }) });
      setSecurity({ enabled: false, configured: false, mode: null, pin: "", confirmPin: "", currentPin: "", newPin: "", confirmNewPin: "" });
      try { sessionStorage.removeItem("resumeai_unlocked"); } catch {}
      setMessage(d.message || "PIN removed successfully.");
    } catch (e) { setMessage(e.message); } finally { setBusy(false); }
  }

  async function handleProfilePhotoChange(event) {
    const selected = event.target.files?.[0];
    if (!selected) return;
    if (!selected.type.startsWith("image/")) { setMessage("Please choose an image file."); return; }
    if (selected.size > 5 * 1024 * 1024) { setMessage("Profile photo must be 5 MB or smaller."); return; }
    try {
      const dataUrl = await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = reject; reader.readAsDataURL(selected); });
      const img = await new Promise((resolve, reject) => { const image = new Image(); image.onload = () => resolve(image); image.onerror = reject; image.src = dataUrl; });
      const size = 512; const canvas = document.createElement("canvas"); canvas.width = size; canvas.height = size; const ctx = canvas.getContext("2d");
      const scale = Math.max(size / img.width, size / img.height); const w = img.width * scale; const h = img.height * scale;
      ctx.drawImage(img, (size - w) / 2, (size - h) / 2, w, h);
      const compressed = canvas.toDataURL("image/jpeg", 0.88);
      setProfile(prev => ({...prev, photo: compressed})); setMessage("Photo selected. Click Save Profile to keep it.");
    } catch { setMessage("Could not read that photo. Please choose another image."); }
  }

  async function saveProfile(e) {
    e.preventDefault(); setBusy(true); setMessage("");
    try { await api("/api/profile", { method: "PUT", body: JSON.stringify(profile) }); localStorage.setItem("resumeai_user", JSON.stringify({ ...currentUser, name: profile.name })); setProfileEditing(false); window.dispatchEvent(new Event("resumeai-profile-updated")); setMessage("Profile saved successfully."); }
    catch (e) { setMessage(e.message); }
    finally { setBusy(false); }
  }

  async function saveSettings(e) {
    e.preventDefault(); setBusy(true); setMessage("");
    try { await api("/api/settings", { method: "PUT", body: JSON.stringify(settings) }); setMessage("Settings saved successfully."); }
    catch (e) { setMessage(e.message); }
    finally { setBusy(false); }
  }

  if (page === "mocks") return <SimplePage title="AI Mock Interviews" icon="🤖" description="Practice with an adaptive AI interviewer that listens, responds and evaluates your answers.">
    <div className="professional-module mock-ai-suite animated-module">
      {!mockSession && !mockResult?.final && <div className="mock-ai-hero">
        <div className="mock-robot-orb">🤖</div>
        <div className="mock-ai-copy"><span className="eyebrow">RESUMEAI AI INTERVIEWER</span><h2>Practice like it is a real interview.</h2><p>The AI reads your resume when available, asks exactly 10 adaptive questions and evaluates each answer before moving forward.</p></div>
        <div className="mock-ai-controls"><label>Target role<input value={mockRole} onChange={e => setMockRole(e.target.value)} placeholder="e.g. Software Engineer" /></label><label>Target goal<input value={mockTargetGoal} onChange={e => setMockTargetGoal(e.target.value)} placeholder="e.g. Crack frontend interviews" /></label><label>Interview language<select value={mockLanguage} onChange={e => setMockLanguage(e.target.value)}><option>English</option><option>Hindi</option><option>Hinglish</option></select></label><div className="mock-mode-picker"><span>Interview mode</span><button type="button" className={mockMode === "text" ? "selected" : ""} onClick={() => setMockMode("text")}>💬 AI + Human Text</button><button type="button" className={mockMode === "voice" ? "selected" : ""} onClick={() => setMockMode("voice")}>🎙️ AI Voice + Human Voice</button></div><button className="workspace-primary glow-action" onClick={startMock} disabled={busy}>{busy ? "Preparing AI Interview..." : "Start 10-Question Interview →"}</button></div>
      </div>}
      {mockSession && <div className="mock-live-shell">
        <div className="mock-live-top"><div><span className="eyebrow">🤖 LIVE AI INTERVIEW</span><h2>{mockSession.role || mockRole}</h2></div><div className="mock-live-actions"><div className="mock-language-chip">🌐 {mockSession.language || mockLanguage}</div><button type="button" className="mock-exit-btn" onClick={endMock}>✕ End Interview</button></div></div>
        <div className="mock-progress"><span>QUESTION {mockNumber} OF 10</span><div><i style={{ width: `${(mockNumber / 10) * 100}%` }} /></div></div>
        <div className="mock-question-bubble"><div className="mock-speaker-line"><span>🤖 AI Interviewer</span>{mockMode === "voice" && <button type="button" className="voice-play-btn" onClick={() => speakAIQuestion(mockSession.question)}>{aiSpeaking ? "🔊 Speaking..." : "🔊 Hear question"}</button>}</div><h2>{mockSession.question}</h2><small className="mock-conversation-hint">{mockMode === "voice" ? "AI asks by voice. You can answer by voice or type your answer below." : "AI asks in chat. Type your answer below, or switch to Voice AI for spoken practice."}</small></div>
        <div className="mock-answer-area"><div className="mock-answer-heading"><div><strong>Your answer</strong><small>Speak or type naturally. The AI evaluates what you actually say.</small></div><button type="button" className={`voice-btn ${mockListening ? "listening" : ""}`} onClick={startVoiceInput}>{mockListening ? "🎙️ Listening..." : "🎙️ Speak answer"}</button></div><textarea rows="8" value={mockAnswer} onChange={e => setMockAnswer(e.target.value)} placeholder={mockLanguage === "Hindi" ? "Apna answer yahan likhein..." : mockLanguage === "Hinglish" ? "Apna answer yahan type karein..." : "Write your answer in your own words..."}/><button className="workspace-primary" onClick={submitMock} disabled={busy || !mockAnswer.trim()}>{busy ? "🤖 Evaluating your answer..." : "Send Answer →"}</button></div>
        {mockResult && !mockResult.final && <div className="mock-next-ready"><div><span className="eyebrow">ANSWER RECORDED</span><h3>Your answer has been saved for the final interview evaluation.</h3><p>No score is shown yet. ResumeAI will evaluate all answers together after Question 10.</p></div><button className="workspace-primary" onClick={nextMockQuestion}>Next AI Question →</button></div>}
      </div>}
      {mockResult?.final && <div className="mock-final-card mock-final-pro"><div className="mock-robot-orb">🏆</div><span className="eyebrow">10 / 10 COMPLETE</span><h2>Mock interview complete.</h2><div className="final-score">{mockResult.final_score}<small>/100</small></div><p>{mockResult.final_feedback}</p><div className="mock-final-report">{(mockResult.final_report || []).map((item, index) => <article className="mock-report-item" key={item.question_number || index}><div className="mock-report-q"><span>Question {item.question_number}</span><strong>{item.question}</strong></div><div className="mock-report-answer"><b>Your answer</b><p>{item.answer || "No answer recorded."}</p></div><div className="mock-report-evaluation"><span className="mock-report-score">{item.score}/100</span><div><b>What went wrong / evaluation</b><p>{item.feedback}</p>{item.strengths && <p><strong>Strength:</strong> {item.strengths}</p>}{item.improvement && <p><strong>Improve:</strong> {item.improvement}</p>}</div></div></article>)}</div><div className="mock-final-actions"><button className="workspace-primary" onClick={startMock}>Start New Interview →</button><button className="secondary-action" onClick={() => onNavigate("analytics")}>View Career Analytics</button></div></div>}
      {message && <p className="module-message">{message}</p>}
    </div>
  </SimplePage>;

  if (page === "jobs") return <SimplePage title="Jobs" icon="💼" description="Find live opportunities ranked against your analyzed resume.">
    <div className="professional-module jobs-module-pro">
      <div className="job-search-bar jobs-header-pro"><div><span className="eyebrow">AI CAREER MATCHING</span><h2>Find jobs that fit your resume</h2><p className="jobs-match-note">{resumeJobId ? "Resume-based matching is ON. Filters below are generated from your analyzed resume." : "Analyze a resume first to unlock resume-based matching and personalized filters."}</p></div><form onSubmit={e => { e.preventDefault(); loadJobs(jobSearch); }}><input value={jobSearch} onChange={e => setJobSearch(e.target.value)} placeholder="Search role, skill or keyword"/><button className="workspace-primary" disabled={busy}>{busy ? "Searching..." : "Search Jobs"}</button></form></div>
      {message && <p className="module-message">{message}</p>}
      <div className="jobs-filter-panel"><div className="jobs-filter-title"><span>🎯</span><div><strong>Smart job filters</strong><small>Role, skill, country, work mode and experience.</small></div></div><select value={jobRoleFilter} onChange={e => setJobRoleFilter(e.target.value)}><option value="">All matching roles</option>{jobFilterOptions.roles.map(x => <option key={x} value={x}>{x}</option>)}</select><select value={jobSkillFilter} onChange={e => setJobSkillFilter(e.target.value)}><option value="">Any resume skill</option>{jobFilterOptions.skills.map(x => <option key={x} value={x}>{x}</option>)}</select><select value={jobExperienceFilter} onChange={e => setJobExperienceFilter(e.target.value)}><option>Any experience</option><option>Entry level</option><option>Mid level</option><option>Senior level</option></select><select value={jobCountryFilter} onChange={e => setJobCountryFilter(e.target.value)}><option>Any country</option>{(jobFilterOptions.countries || []).filter(x => x !== "Any country").map(x => <option key={x}>{x}</option>)}</select><select value={jobWorkModeFilter} onChange={e => setJobWorkModeFilter(e.target.value)}>{(jobFilterOptions.work_modes || ["Any","Remote","Hybrid","On-site"]).map(x => <option key={x}>{x}</option>)}</select><select value={jobLocationFilter} onChange={e => setJobLocationFilter(e.target.value)}><option value="">Any location</option>{jobFilterOptions.locations.map(x => <option key={x} value={x}>{x}</option>)}</select><button type="button" className="jobs-apply-filter" onClick={() => loadJobs(jobSearch)}>Apply Filters</button><button type="button" className="jobs-clear-filter" onClick={() => { setJobRoleFilter(""); setJobSkillFilter(""); setJobLocationFilter(""); setJobExperienceFilter("Any experience"); setJobCountryFilter("Any country"); setJobWorkModeFilter("Any"); window.setTimeout(() => loadJobs(jobSearch), 0); }}>Clear</button></div>
      <div className="job-grid">{jobs.map(job => <article className="job-card" key={job.id}><div className="job-card-top"><span className="job-company-icon">💼</span>{resumeJobId && <span className="job-match-pill">{job.match_score || 0}% MATCH</span>}</div><h3>{job.title}</h3><p className="job-company">{job.company}</p><p className="job-location">📍 {job.location || "Remote"}</p><a href={job.url} target="_blank" rel="noreferrer" className="job-link">View Job →</a></article>)}{!jobs.length && !busy && <div className="empty-module"><span>🔎</span><h3>No matching jobs</h3><p>Try another role, skill or filter.</p></div>}</div><small className="source-note">Live job listings may change or expire. Match scores are based on evidence detected in the analyzed resume.</small>
    </div>
  </SimplePage>;

  if (page === "applications") return <SimplePage title="My Applications" icon="📋" description="Track your real job applications, statuses and notes in one place.">
    <div className="professional-module applications-pro animated-module">
      <div className="applications-pro-header">
        <div>
          <span className="eyebrow">CAREER TRACKER</span>
          <h2>My Applications</h2>
          <p>One clean place to manage every opportunity and see your progress.</p>
        </div>
        <button className="workspace-primary glow-action" onClick={() => document.getElementById("application-form")?.scrollIntoView({ behavior: "smooth" })}>＋ Add Application</button>
      </div>
      <div className="application-kpi-grid application-kpi-pro">
        {[
          ["📋", "Total Applications", applications.length, "kpi-blue"],
          ["📨", "Applied", applications.filter(a => a.status === "Applied").length, "kpi-sky"],
          ["🎤", "Interviews", applications.filter(a => a.status === "Interview").length, "kpi-purple"],
          ["🏆", "Offers", applications.filter(a => a.status === "Offer").length, "kpi-green"],
        ].map(([icon, label, value, tone]) => (
          <div className={`application-kpi ${tone}`} key={label}>
            <span>{icon}</span><div><small>{label}</small><strong>{value}</strong><em>Live account data</em></div>
          </div>
        ))}
      </div>
      <div className="applications-workspace-grid">
        <section className="application-panel application-add-panel">
          <div className="panel-heading"><span>✨</span><div><h3>Add an opportunity</h3><p>Save a job you want to track.</p></div></div>
          <form id="application-form" className="application-form application-form-pro application-form-modern" onSubmit={saveApplication}>
            <label>Company<input placeholder="e.g. Google" value={appForm.company} onChange={e => setAppForm({...appForm,company:e.target.value})} required/></label>
            <label>Role<input placeholder="e.g. Software Engineer" value={appForm.role} onChange={e => setAppForm({...appForm,role:e.target.value})} required/></label>
            <label>Location<input placeholder="Remote / City" value={appForm.location} onChange={e => setAppForm({...appForm,location:e.target.value})}/></label>
            <label>Status<select value={appForm.status} onChange={e => setAppForm({...appForm,status:e.target.value})}><option>Applied</option><option>Interview</option><option>Offer</option><option>Rejected</option><option>Withdrawn</option></select></label>
            <label className="application-notes-field">Job URL<input placeholder="https://..." value={appForm.url} onChange={e => setAppForm({...appForm,url:e.target.value})}/></label>
            <label className="application-notes-field">Notes<textarea rows="3" placeholder="Interview date, recruiter notes, next step..." value={appForm.notes} onChange={e => setAppForm({...appForm,notes:e.target.value})}/></label>
            <button className="workspace-primary" disabled={busy}>{busy ? "Saving..." : "Save Application →"}</button>
          </form>
        </section>
        <section className="application-panel application-list-panel">
          <div className="panel-heading"><span>📈</span><div><h3>Application timeline</h3><p>Your saved opportunities appear here.</p></div></div>
          <div className="application-list application-list-pro">
            {applications.map(a => <article className="application-card application-card-pro animated-row" key={a.id}>
              <div className="application-company-mark">{(a.company || "C").slice(0,1).toUpperCase()}</div>
              <div className="application-main">
                <div className="application-title-line"><h3>{a.company}</h3><span className={`application-status status-${String(a.status || "Applied").toLowerCase()}`}>{a.status}</span></div>
                <p>{a.role}</p><small>📍 {a.location || "Location not specified"}</small>
                {a.url && <a href={a.url} target="_blank" rel="noreferrer">Open Job Posting ↗</a>}
              </div>
              <div className="application-actions"><select value={a.status} onChange={e => updateApplication(a.id,e.target.value)} aria-label={`Update ${a.company} status`}><option>Applied</option><option>Interview</option><option>Offer</option><option>Rejected</option><option>Withdrawn</option></select><button className="danger-ghost" onClick={() => deleteApplication(a.id)}>Delete</button></div>
            </article>)}
            {!applications.length && <div className="empty-module application-empty"><span>🚀</span><h3>Your application tracker is ready</h3><p>Add your first opportunity and start building your career pipeline.</p></div>}
          </div>
        </section>
      </div>
      {message && <p className="module-message">{message}</p>}
    </div>
  </SimplePage>;

  const safeProfile = {
    name: typeof profile?.name === "string" ? profile.name : (currentUser?.name || ""),
    email: typeof profile?.email === "string" ? profile.email : (currentUser?.email || ""),
    phone: typeof profile?.phone === "string" ? profile.phone : "",
    location: typeof profile?.location === "string" ? profile.location : "",
    headline: typeof profile?.headline === "string" ? profile.headline : "",
    bio: typeof profile?.bio === "string" ? profile.bio : "",
    skills: Array.isArray(profile?.skills) ? profile.skills.join(", ") : (typeof profile?.skills === "string" ? profile.skills : ""),
    photo: typeof profile?.photo === "string" ? profile.photo : ""
  };
  const safeSkillCount = safeProfile.skills.split(/[,|\n]/).map(v => v.trim()).filter(Boolean).length;

  if (page === "profile") return <SimplePage title="Profile" icon="👤" description="Build the professional identity ResumeAI uses across your career workspace.">
    <div className="professional-module profile-command-center animated-module">
      <div className="profile-hero-pro">
        <div className="profile-avatar-xl profile-avatar-gradient profile-avatar-photo">{safeProfile.photo ? <img src={safeProfile.photo} alt="Profile"/> : (safeProfile.name || "U").slice(0,1).toUpperCase()}</div>
        <div className="profile-hero-copy"><span className="eyebrow">CAREER IDENTITY</span><h2>{safeProfile.name || "Your Name"} <span className="verified-dot">✓</span></h2><p>{safeProfile.headline || "Add a professional headline to make your profile stronger."}</p><div className="profile-meta"><span>✉️ {safeProfile.email || "Email not added"}</span><span>📍 {safeProfile.location || "Location not added"}</span></div></div>
        <div className="profile-hero-actions"><button type="button" className="secondary-action" onClick={() => setProfileEditing(v => !v)}>{profileEditing ? "Cancel Edit" : "✏️ Edit Profile"}</button><div className="profile-completion-ring"><strong>{Math.min(100, Math.round(([safeProfile.name,safeProfile.email,safeProfile.phone,safeProfile.location,safeProfile.headline,safeProfile.bio,safeProfile.skills].filter(Boolean).length / 7) * 100))}%</strong><small>Complete</small></div></div>
      </div>
      <div className="profile-insight-grid"><div><span>🎯</span><small>Career readiness</small><strong>{safeProfile.headline && safeProfile.skills ? "Ready" : "In progress"}</strong></div><div><span>🧠</span><small>Skills listed</small><strong>{safeSkillCount}</strong></div><div><span>📄</span><small>Resume analysis</small><strong>{resumeJobId ? "Analyzed" : "Not analyzed"}</strong></div><div><span>🎤</span><small>Interview practice</small><strong>10 questions</strong></div></div>
      <form className="profile-editor-pro" onSubmit={saveProfile}><div className="profile-editor-title"><span>✨</span><div><h3>Professional profile</h3><p>Edit the details ResumeAI uses across your career workspace.</p></div></div>
        <div className="profile-photo-editor"><div className="profile-photo-editor-preview">{safeProfile.photo ? <img src={safeProfile.photo} alt="Selected profile"/> : (safeProfile.name || "U").slice(0,1).toUpperCase()}</div><div><strong>Profile photo</strong><p>Choose any JPG, PNG or WEBP image. ResumeAI stores a resized copy for your profile.</p><div className="profile-photo-actions">{profileEditing && <label className="secondary-action photo-upload-label">📷 Change Photo<input type="file" accept="image/jpeg,image/png,image/webp" onChange={handleProfilePhotoChange} hidden/></label>}{profileEditing && safeProfile.photo && <button type="button" className="danger-ghost secondary-action" onClick={() => setProfile(prev => ({...prev,photo: ""}))}>Remove Photo</button>}</div></div></div>
        <div className="profile-field-grid"><label>Full Name<input disabled={!profileEditing} value={safeProfile.name} onChange={e=>setProfile({...profile,name:e.target.value})} placeholder="Your name" required/></label><label>Email Address<input value={safeProfile.email} readOnly/></label><label>Phone Number<input disabled={!profileEditing} value={safeProfile.phone} onChange={e=>setProfile({...profile,phone:e.target.value})} placeholder="+91 ..."/></label><label>Location<input disabled={!profileEditing} value={safeProfile.location} onChange={e=>setProfile({...profile,location:e.target.value})} placeholder="City, Country"/></label><label className="full">Professional Headline<input disabled={!profileEditing} value={safeProfile.headline} onChange={e=>setProfile({...profile,headline:e.target.value})} placeholder="e.g. Software Developer | React & Python"/></label><label className="full">Professional Summary<textarea disabled={!profileEditing} rows="5" value={safeProfile.bio} onChange={e=>setProfile({...profile,bio:e.target.value})} placeholder="Write a concise introduction based on your real experience..."/></label><label className="full">Skills & Technologies<textarea disabled={!profileEditing} rows="3" value={safeProfile.skills} onChange={e=>setProfile({...profile,skills:e.target.value})} placeholder="Python, React, FastAPI, SQL..."/></label></div>
        {profileEditing && <div className="profile-form-footer full"><span>🔒 Your changes are saved when you click Save Profile.</span><button className="workspace-primary glow-action" disabled={busy}>{busy ? "Saving..." : "Save Profile →"}</button></div>}
      </form>{message && <p className="module-message">{message}</p>}
    </div>
  </SimplePage>;

  if (page === "settings") return <SimplePage title="Settings" icon="⚙️" description="Control your ResumeAI workspace, appearance and AI experience.">
    <div className="professional-module settings-command-center animated-module">
      <div className="settings-pro-header"><div><span className="eyebrow">CONTROL CENTER</span><h2>Settings</h2><p>Every control below is interactive and saves to your ResumeAI workspace.</p></div><div className="settings-gear">⚙️</div></div>
      <div className="settings-layout settings-layout-pro">
        <aside className="settings-nav-card settings-nav-interactive">{[['👤','Account','Personal details and account information'],['🎨','Appearance','Theme and display preferences'],['🔔','Notifications','Email and weekly updates'],['📄','Resume Preferences','Resume upload and analysis'],['🤖','AI Preferences','AI assistant and suggestions'],['🔐','Security','Password and session management']].map(([icon,title,sub])=><button type="button" className={`settings-nav-item ${settingsTab===title?'active':''}`} key={title} onClick={()=>setSettingsTab(title)}><span>{icon}</span><div><strong>{title}</strong><small>{sub}</small></div><b>›</b></button>)}</aside>
        <section className="settings-content-card settings-content-pro">
          {settingsTab === "Account" && <div className="settings-pane"><div className="settings-pane-head"><span>👤</span><div><h3>Account</h3><p>Your identity and account information.</p></div></div><div className="settings-account-preview"><div className="settings-avatar">{(currentUser?.name || profile.name || "U").slice(0,1).toUpperCase()}</div><div><strong>{currentUser?.name || profile.name || "ResumeAI User"}</strong><small>{profile.email || currentUser?.email || "Guest workspace"}</small>{currentUser?.email && <small>Signed in with: {currentUser.email}</small>}</div><span>✓ Workspace active</span></div><div className="settings-account-premium"><div><span>👑</span><div><strong>ResumeAI Premium</strong><small>Advanced career tools and future premium features.</small></div></div><b>🚀 Coming Soon</b></div><button className="secondary-action" type="button" onClick={()=>onNavigate("profile")}>Open Full Profile →</button></div>}
          {settingsTab === "Appearance" && <div className="settings-pane"><div className="settings-pane-head"><span>🎨</span><div><h3>Appearance</h3><p>Choose how ResumeAI looks on your device.</p></div></div><div className="theme-choice-grid">{[['light','☀️','Light','Clean bright workspace'],['dark','🌙','Dark','Low-light focused workspace']].map(([value,icon,title,sub])=><button type="button" key={value} className={`theme-choice ${settings.theme===value?'selected':''}`} onClick={()=>setSettings({...settings,theme:value})}><span>{icon}</span><strong>{title}</strong><small>{sub}</small>{settings.theme===value && <b>✓</b>}</button>)}</div><div className="settings-live-note">✨ Theme changes apply immediately.</div></div>}
          {settingsTab === "Notifications" && <div className="settings-pane"><div className="settings-pane-head"><span>🔔</span><div><h3>Notifications</h3><p>Choose which career updates you want.</p></div></div><div className="settings-toggle-list"><div className="settings-row-pro"><div><h3>Email notifications</h3><p>Important account and feature updates.</p></div><label className="toggle"><input type="checkbox" checked={settings.email_notifications} onChange={e=>setSettings({...settings,email_notifications:e.target.checked})}/><span/></label></div><div className="settings-row-pro"><div><h3>Weekly career summary</h3><p>A compact summary of your ResumeAI activity.</p></div><label className="toggle"><input type="checkbox" checked={settings.weekly_summary} onChange={e=>setSettings({...settings,weekly_summary:e.target.checked})}/><span/></label></div></div></div>}
          {settingsTab === "Resume Preferences" && <div className="settings-pane"><div className="settings-pane-head"><span>📄</span><div><h3>Resume Preferences</h3><p>Controls for your resume workflow.</p></div></div><div className="preference-cards"><div><strong>Supported formats</strong><span>PDF · DOC · DOCX · RTF · ODT · TXT · JPG · JPEG · PNG · WEBP</span></div><div><strong>Analysis style</strong><span>Evidence-based and honest scoring</span></div><div><strong>Enhancement</strong><span>Original photo preserved when available</span></div></div><div className="settings-live-note">💡 ResumeAI will never treat a suggestion as a fact from your resume.</div></div>}
          {settingsTab === "AI Preferences" && <div className="settings-pane"><div className="settings-pane-head"><span>🤖</span><div><h3>AI Preferences</h3><p>Control how AI Career Chat and AI tools respond.</p></div></div><label className="settings-select-card"><span>Website language</span><small>Change the language of the ResumeAI interface.</small><select value={settings.language} onChange={e=>setSettings({...settings,language:e.target.value})}><option>English</option><option>Hindi</option></select></label><div className="settings-voice-card"><div><span>🎙️</span><div><strong>AI Interview Voice</strong><small>Choose whether the AI interviewer speaks and which voice style it uses.</small></div></div><label className="toggle"><input type="checkbox" checked={settings.voice_enabled} onChange={e=>setSettings({...settings,voice_enabled:e.target.checked})}/><span/></label><select value={settings.voice_gender} onChange={e=>setSettings({...settings,voice_gender:e.target.value})}><option value="female">Female voice</option><option value="male">Male voice</option></select><button type="button" className="voice-preview-setting" onClick={previewVoice}>▶ Test Voice</button></div><div className="ai-capability-grid"><span>🧠 Resume-grounded feedback</span><span>🎤 Adaptive mock interviews</span><span>💬 Multilingual chat</span><span>🔎 Evidence-aware suggestions</span></div></div>}
          {settingsTab === "Security" && (
            <div className="settings-pane">
              <div className="settings-pane-head">
                <span>🔐</span>
                <div>
                  <h3>Security</h3>
                  <p>Your PIN is never displayed or included in normal settings auto-save.</p>
                </div>
              </div>

              <div className="security-panel">
                <div>
                  <span>🛡️</span>
                  <strong>{currentUser ? "Account session" : "Guest workspace"}</strong>
                  <small>{currentUser ? "Signed-in session is active." : "PIN lock is available after account login."}</small>
                </div>
                <span className={`security-status-badge ${security.enabled ? "on" : "off"}`}>
                  {security.enabled ? "🔒 LOCK ON" : "🔓 LOCK OFF"}
                </span>
              </div>

              {currentUser && (
                <div className="security-lock-card">
                  {!security.configured ? (
                    <div className="security-setup">
                      <div>
                        <h3>Create Website PIN</h3>
                        <p>Choose a 4-12 digit PIN. It is saved only after you click Set PIN.</p>
                      </div>
                      <input
                        className="security-pin-input"
                        inputMode="numeric"
                        pattern="[0-9]*"
                        maxLength="12"
                        type="password"
                        placeholder="Create PIN"
                        value={security.pin}
                        onChange={e => setSecurity({ ...security, pin: e.target.value.replace(/\D/g, "") })}
                      />
                      <input
                        className="security-pin-input"
                        inputMode="numeric"
                        pattern="[0-9]*"
                        maxLength="12"
                        type="password"
                        placeholder="Confirm PIN"
                        value={security.confirmPin}
                        onChange={e => setSecurity({ ...security, confirmPin: e.target.value.replace(/\D/g, "") })}
                      />
                      <button type="button" className="workspace-primary" onClick={setupSecurityPin} disabled={busy}>
                        🔐 Set PIN
                      </button>
                    </div>
                  ) : (
                    <div>
                      <div className="security-configured-row">
                        <div>
                          <h3>Website Lock</h3>
                          <p>{security.enabled ? "Your workspace is protected." : "Your PIN is configured but website lock is currently off."}</p>
                        </div>
                        <span className="security-pin-hidden">••••••••</span>
                      </div>

                      {security.mode === "change" && (
                        <div className="security-form">
                          <input
                            className="security-pin-input"
                            inputMode="numeric"
                            maxLength="12"
                            type="password"
                            placeholder="Current PIN"
                            value={security.currentPin}
                            onChange={e => setSecurity({ ...security, currentPin: e.target.value.replace(/\D/g, "") })}
                          />
                          <input
                            className="security-pin-input"
                            inputMode="numeric"
                            maxLength="12"
                            type="password"
                            placeholder="New PIN"
                            value={security.newPin}
                            onChange={e => setSecurity({ ...security, newPin: e.target.value.replace(/\D/g, "") })}
                          />
                          <input
                            className="security-pin-input"
                            inputMode="numeric"
                            maxLength="12"
                            type="password"
                            placeholder="Confirm New PIN"
                            value={security.confirmNewPin}
                            onChange={e => setSecurity({ ...security, confirmNewPin: e.target.value.replace(/\D/g, "") })}
                          />
                          <div className="security-action-row">
                            <button type="button" className="workspace-primary" onClick={changeSecurityPin} disabled={busy}>Change PIN</button>
                            <button type="button" className="secondary-action" onClick={() => setSecurity({ ...security, mode: null, currentPin: "", newPin: "", confirmNewPin: "" })}>Cancel</button>
                          </div>
                        </div>
                      )}

                      {security.mode === "enable" && (
                        <div className="security-form">
                          <input
                            className="security-pin-input"
                            inputMode="numeric"
                            maxLength="12"
                            type="password"
                            placeholder="Enter current PIN to enable lock"
                            value={security.currentPin}
                            onChange={e => setSecurity({ ...security, currentPin: e.target.value.replace(/\D/g, "") })}
                          />
                          <div className="security-action-row">
                            <button type="button" className="workspace-primary" onClick={enableSecurityLock} disabled={busy}>Enable Lock</button>
                            <button type="button" className="secondary-action" onClick={() => setSecurity({ ...security, mode: null, currentPin: "" })}>Cancel</button>
                          </div>
                        </div>
                      )}

                      {security.mode === "disable" && (
                        <div className="security-form">
                          <input className="security-pin-input" inputMode="numeric" maxLength="12" type="password" placeholder="Enter current PIN to disable lock" value={security.currentPin} onChange={e => setSecurity({ ...security, currentPin: e.target.value.replace(/\D/g, "") })} />
                          <div className="security-action-row">
                            <button type="button" className="danger-ghost secondary-action" onClick={disableSecurityLock} disabled={busy}>Disable Lock</button>
                            <button type="button" className="secondary-action" onClick={() => setSecurity({ ...security, mode: null, currentPin: "" })}>Cancel</button>
                          </div>
                        </div>
                      )}

                      {security.mode === "remove" && (
                        <div className="security-form">
                          <p className="security-warning">Removing the PIN will also turn off Website Lock. You must verify your current PIN.</p>
                          <input className="security-pin-input" inputMode="numeric" maxLength="12" type="password" placeholder="Enter current PIN" value={security.currentPin} onChange={e => setSecurity({ ...security, currentPin: e.target.value.replace(/\D/g, "") })} />
                          <div className="security-action-row">
                            <button type="button" className="danger-ghost secondary-action" onClick={removeSecurityPin} disabled={busy}>Remove PIN</button>
                            <button type="button" className="secondary-action" onClick={() => setSecurity({ ...security, mode: null, currentPin: "" })}>Cancel</button>
                          </div>
                        </div>
                      )}

                      {!security.mode && (
                        <div className="security-action-row">
                          {security.enabled ? (
                            <button type="button" className="secondary-action" onClick={() => setSecurity({ ...security, mode: "disable", currentPin: "" })}>Turn Off Lock</button>
                          ) : (
                            <button type="button" className="workspace-primary" onClick={() => setSecurity({ ...security, mode: "enable", currentPin: "" })}>Enable Lock</button>
                          )}
                          <button type="button" className="secondary-action" onClick={() => setSecurity({ ...security, mode: "change", currentPin: "" })}>Change PIN</button>
                          <button type="button" className="danger-ghost secondary-action" onClick={() => setSecurity({ ...security, mode: "remove", currentPin: "" })}>Remove PIN</button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
          <div className="settings-save-bar"><span>✓ All changes auto-save automatically after a short delay.</span><span className="auto-save-live">LIVE</span></div>
        </section>
      </div>{message && <p className="module-message">{message}</p>}
    </div>
  </SimplePage>;

  if (page === "analytics") return <SimplePage title="Analytics" icon="📊" description="Real activity recorded in your ResumeAI account."><div className="analytics-grid-pro"><div className="analytics-card"><span>📋</span><small>Applications</small><strong>{analytics?.applications ?? "—"}</strong></div><div className="analytics-card"><span>🎤</span><small>Mock Interviews</small><strong>{analytics?.mock_interviews ?? "—"}</strong></div><div className="analytics-card"><span>🎯</span><small>Average Mock Score</small><strong>{analytics?.average_mock_score != null ? `${analytics.average_mock_score}%` : "—"}</strong></div></div>{message && <p className="module-message">{message}</p>}</SimplePage>;

  if (page === "premium") return <SimplePage title="ResumeAI Future Lab" icon="👑" description="Next-generation career features planned for future ResumeAI releases.">
    <div className="professional-module premium-command-center animated-module">
      <div className="premium-hero premium-hero-live"><div className="premium-crown">🤖👑</div><span className="eyebrow">RESUMEAI FUTURE LAB</span><h2>What we are building next.</h2><p>These ideas are intentionally marked Coming Soon. They are not fake unlocks and will only appear as real features when implemented.</p></div>
      <div className="premium-feature-grid premium-feature-grid-live premium-coming-grid">
        {[
          ["🧩","AI Resume Tailoring","Automatically adapt one resume to a specific job description while keeping your real experience intact."],
          ["🧠","Career Skill Gap Map","Compare your demonstrated skills with a target role and create a practical learning roadmap."],
          ["🎥","AI Video Interview Coach","Practice camera-based interview answers with feedback on clarity, structure and delivery."],
          ["📈","Career Growth Forecast","Track resume, applications and interview progress to show how your job-readiness is changing over time."],
          ["🌐","Personal Job Match Engine","Rank opportunities against your actual resume, preferences and demonstrated skills instead of generic keywords."],
          ["🗂️","Smart Resume Version Manager","Keep multiple role-specific resume versions organized and compare what changed between them."]
        ].map(([icon,title,desc])=><article className="premium-feature-live premium-coming-card" key={title}><span className="premium-feature-icon">{icon}</span><div><strong>{title}</strong><p>{desc}</p><b>🚀 Coming Soon</b></div></article>)}
      </div>
    </div>
  </SimplePage>;

  return null;
}

function SimplePage({ title, icon, description, children }) {
  return (
    <main className="workspace-page">
      <div className="workspace-welcome">
        <div>
          <span className="workspace-eyebrow">RESUMEAI</span>
          <h1>{icon} {title}</h1>
          <p>{description}</p>
        </div>
      </div>
      <section className="workspace-card workspace-full-card">{children}</section>
    </main>
  );
}

function App() {
  const [activePage, setActivePage] = useState("resume");
  const [accountOpen, setAccountOpen] = useState(false);

  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [signupName, setSignupName] = useState("");
  const [signupEmail, setSignupEmail] = useState("");
  const [signupPassword, setSignupPassword] = useState("");
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("resumeai_user")) || null;
    } catch {
      return null;
    }
  });
  const [authLoading, setAuthLoading] = useState(false);
  const [authMessage, setAuthMessage] = useState("");
  const [authMessageType, setAuthMessageType] = useState("");
  const [notifications, setNotifications] = useState([]);
  const [notificationOpen, setNotificationOpen] = useState(false);
  const [siteLocked, setSiteLocked] = useState(false);
  const [lockPin, setLockPin] = useState("");
  const [lockMessage, setLockMessage] = useState("");
  const [globalProfilePhoto, setGlobalProfilePhoto] = useState("");
  const [uiLanguage, setUiLanguage] = useState(() => { try { return localStorage.getItem("resumeai_ui_language") === "Hindi" ? "Hindi" : "English"; } catch { return "English"; } });
  const [uiTheme, setUiTheme] = useState(() => { try { return localStorage.getItem("resumeai_theme") === "dark" ? "dark" : "light"; } catch { return "light"; } });

  useEffect(() => {
    const syncLanguage = (event) => setUiLanguage(event?.detail === "Hindi" ? "Hindi" : "English");
    const syncTheme = (event) => setUiTheme(event?.detail === "dark" ? "dark" : "light");
    window.addEventListener("resumeai-language-updated", syncLanguage);
    window.addEventListener("resumeai-theme-updated", syncTheme);
    const initialLanguage = (() => { try { return localStorage.getItem("resumeai_ui_language"); } catch { return null; } })();
    const initialTheme = (() => { try { return localStorage.getItem("resumeai_theme"); } catch { return null; } })();
    if (initialLanguage) setUiLanguage(initialLanguage === "Hindi" ? "Hindi" : "English");
    if (initialTheme) setUiTheme(initialTheme === "dark" ? "dark" : "light");
    return () => {
      window.removeEventListener("resumeai-language-updated", syncLanguage);
      window.removeEventListener("resumeai-theme-updated", syncTheme);
    };
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("resumeai-dark", uiTheme === "dark");
    document.documentElement.classList.remove("resumeai-neon");
  }, [uiTheme]);

  useEffect(() => installUiLanguageObserver(uiLanguage), [uiLanguage]);

  const [dashboardStats, setDashboardStats] = useState({
    total_resumes: 0,
    latest_score: null,
    mock_interviews: 0,
    applications: 0,
    average_mock_score: null,
  });

  const [file, setFile] = useState(null);

  const [photo, setPhoto] = useState(null);
  const [photoPreview, setPhotoPreview] =
    useState("");

  const [result, setResult] = useState(() => {
    try { return JSON.parse(localStorage.getItem("resumeai_last_analysis")) || null; } catch { return null; }
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [aiAdvice, setAiAdvice] = useState(null);
  const [aiStatus, setAiStatus] = useState("");

  const [chatMessages, setChatMessages] =
    useState([]);

  const [chatInput, setChatInput] =
    useState("");

  const [chatLoading, setChatLoading] =
    useState(false);

  const [enhancing, setEnhancing] =
    useState(false);

  const [checkingPhoto, setCheckingPhoto] =
    useState(false);

  const [
    showEnhancePhotoOptions,
    setShowEnhancePhotoOptions,
  ] = useState(false);

  const [
    originalPhotoDetected,
    setOriginalPhotoDetected,
  ] = useState(null);

  const [enhancedResume, setEnhancedResume] =
    useState("");

  const [enhancedPhotoDataUrl, setEnhancedPhotoDataUrl] =
    useState("");

  const [enhancedPdf, setEnhancedPdf] =
    useState("");

  const [
    enhancedFilename,
    setEnhancedFilename,
  ] = useState("");

  const [selectedEnhanceTemplate, setSelectedEnhanceTemplate] =
    useState("professional");

  const [templateGenerating, setTemplateGenerating] =
    useState(false);

  const [enhanceError, setEnhanceError] =
    useState("");

  const [
    showScoreDetails,
    setShowScoreDetails,
  ] = useState(false);

  const resumeJobId =
    result?.resume_job_id ||
    result?.job_id ||
    result?.ai_feedback_job_id;

  const score = Number(
    result?.score || 0
  );

  const scoreInfo =
    getScoreInfo(score);

  const detectedSections =
    canonicalSections(
      result?.detected_sections ||
        result?.sections ||
        []
    );

  const skills = Array.isArray(
    result?.skills
  )
    ? result.skills
    : Array.isArray(
        result?.skills_detected
      )
      ? result.skills_detected
      : [];

  const strengths = Array.isArray(
    result?.strengths
  )
    ? result.strengths
    : [];

  const suggestions = Array.isArray(
    result?.suggestions
  )
    ? result.suggestions
    : [];

  const actionPlan =
    Array.isArray(
      result?.action_plan
    ) &&
    result.action_plan.length > 0
      ? result.action_plan
      : suggestions;

  const breakdown =
    result?.breakdown || {};

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const googleToken = params.get("google_token");
    const googleError = params.get("google_error");
    if (googleToken) {
      localStorage.setItem("resumeai_token", googleToken);
      fetch(`${API_URL}/auth/me`, { headers: { Authorization: `Bearer ${googleToken}` } })
        .then(r => r.json())
        .then(d => {
          if (d?.user) { localStorage.setItem("resumeai_user", JSON.stringify(d.user)); setCurrentUser(d.user); setActivePage("dashboard"); }
        })
        .catch(() => setAuthMessage("Google login completed, but the session could not be loaded."));
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (googleError) {
      setAuthMessage(googleError);
      setAuthMessageType("error");
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  useEffect(() => {
    const loadProfilePhoto = () => {
      if (!currentUser || !localStorage.getItem("resumeai_token")) { setGlobalProfilePhoto(""); return; }
      fetch(`${API_URL}/api/profile`, { headers: apiAuthHeaders() }).then(r => r.ok ? r.json() : null).then(d => setGlobalProfilePhoto(d?.profile?.photo || "")).catch(() => {});
    };
    loadProfilePhoto();
    window.addEventListener("resumeai-profile-updated", loadProfilePhoto);
    return () => window.removeEventListener("resumeai-profile-updated", loadProfilePhoto);
  }, [currentUser]);

  useEffect(() => {
    if (!currentUser || !localStorage.getItem("resumeai_token")) { setSiteLocked(false); return; }
    let unlockedThisSession = false;
    try { unlockedThisSession = sessionStorage.getItem("resumeai_unlocked") === "1"; } catch {}
    fetch(`${API_URL}/api/security/status`, { headers: apiAuthHeaders() })
      .then(r => r.ok ? r.json() : null)
      .then(d => { setSiteLocked(!!d?.lock_enabled && !unlockedThisSession); })
      .catch(() => {});
  }, [currentUser]);

  async function unlockSite() {
    setLockMessage("");
    try {
      const response = await fetch(`${API_URL}/api/security/verify-lock`, { method: "POST", headers: { "Content-Type": "application/json", ...apiAuthHeaders() }, body: JSON.stringify({ pin: lockPin }) });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.verified) throw new Error(data.message || "Incorrect PIN.");
      setSiteLocked(false); setLockPin("");
      try { sessionStorage.setItem("resumeai_unlocked", "1"); } catch {}
    } catch (e) { setLockMessage(e.message || "Incorrect PIN."); }
  }

  useEffect(() => {
    if (!currentUser && !localStorage.getItem("resumeai_token")) { setNotifications([]); return; }
    fetch(`${API_URL}/api/notifications`, { headers: apiAuthHeaders() })
      .then(r => r.ok ? r.json() : null)
      .then(d => setNotifications(d?.notifications || []))
      .catch(() => {});
  }, [currentUser, activePage]);

  async function markNotificationRead(id) {
    try {
      await fetch(`${API_URL}/api/notifications/${id}/read`, { method: "POST", headers: apiAuthHeaders() });
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: 1 } : n));
    } catch {}
  }

  useEffect(() => {
    fetch(`${API_URL}/api/dashboard`, {
      headers: apiAuthHeaders(),
    })
      .then(async (response) => {
        const data = await response.json().catch(() => ({}));
        if (response.status === 401) {
          return null;
        }
        if (!response.ok) throw new Error(data.detail || "Could not load dashboard.");
        return data;
      })
      .then((data) => {
        if (data?.dashboard) setDashboardStats(data.dashboard);
      })
      .catch((err) => console.error("Dashboard load failed:", err));
  }, [currentUser]);

  function handleFileChange(event) {
    const selectedFile =
      event.target.files?.[0];

    if (!selectedFile) return;

    setFile(selectedFile);

    setPhoto(null);
    setPhotoPreview("");

    setResult(null);
    try { localStorage.removeItem("resumeai_last_analysis"); } catch {}
    setError("");

    setAiAdvice(null);
    setAiStatus("");

    setEnhancedResume("");
    setEnhancedPhotoDataUrl("");
    setEnhancedPdf("");
    setEnhancedFilename("");
    setSelectedEnhanceTemplate("professional");
    setEnhanceError("");

    setShowEnhancePhotoOptions(false);
    setCheckingPhoto(false);
    setOriginalPhotoDetected(null);

    setShowScoreDetails(false);

    setChatMessages([]);
    setChatInput("");
  }

  function handlePhotoChange(event) {
    const selectedPhoto =
      event.target.files?.[0];

    if (!selectedPhoto) return;

    if (
      ![
        "image/jpeg",
        "image/png",
      ].includes(selectedPhoto.type)
    ) {
      setEnhanceError(
        "Please select a JPG or PNG photo."
      );
      return;
    }

    setPhoto(selectedPhoto);
    setEnhanceError("");

    const url =
      URL.createObjectURL(
        selectedPhoto
      );

    setPhotoPreview(url);
  }

  async function fetchAIAdvice(jobId) {
    setAiStatus("processing");

    for (let i = 0; i < 80; i += 1) {
      try {
        const response =
          await fetch(
            `${API_URL}/ai-feedback/${jobId}`
          );

        const data =
          await response.json();

        if (
          data.status ===
          "completed"
        ) {
          setAiAdvice(
            data.ai_feedback
          );

          setAiStatus(
            "completed"
          );

          return;
        }

        if (
          data.status === "failed"
        ) {
          setAiStatus("failed");
          return;
        }
      } catch {
        // Keep polling.
      }

      await new Promise(
        (resolve) =>
          setTimeout(
            resolve,
            1500
          )
      );
    }

    setAiStatus("failed");
  }

  async function analyzeResume() {
    if (!file) {
      setError(
        "Please select a resume first."
      );
      return;
    }

    setLoading(true);
    setError("");

    setResult(null);
    setAiAdvice(null);
    setAiStatus("");

    setEnhancedResume("");
    setEnhancedPdf("");
    setEnhancedFilename("");
    setSelectedEnhanceTemplate("professional");
    setEnhanceError("");

    setShowEnhancePhotoOptions(
      false
    );

    setCheckingPhoto(false);
    setOriginalPhotoDetected(null);

    setPhoto(null);
    setPhotoPreview("");

    setShowScoreDetails(false);

    setChatMessages([]);
    setChatInput("");

    try {
      const formData =
        new FormData();

      formData.append(
        "file",
        file
      );

      const response =
        await fetch(
          `${API_URL}/analyze`,
          {
            method: "POST",
            headers: apiAuthHeaders(),
            body: formData,
          }
        );

      const data =
        await response.json();

      if (
        !response.ok ||
        !data.success
      ) {
        throw new Error(
          data.message ||
            "Resume analysis failed."
        );
      }

      setResult(data);
      try { localStorage.setItem("resumeai_last_analysis", JSON.stringify(data)); } catch {}

      fetch(`${API_URL}/api/dashboard`, {
        headers: apiAuthHeaders(),
      })
        .then((r) => r.ok ? r.json() : null)
        .then((d) => {
          if (d?.dashboard) setDashboardStats(d.dashboard);
        })
        .catch(() => {});

      const jobId =
        data.resume_job_id ||
        data.ai_feedback_job_id ||
        data.job_id;

      if (jobId) {
        fetchAIAdvice(jobId);
      }
    } catch (err) {
      setError(
        err.message ||
          "Could not analyze the resume."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleEnhanceClick() {
    if (!resumeJobId) {
      setEnhanceError(
        "Please analyze a resume first."
      );
      return;
    }

    if (!file) {
      setEnhanceError(
        "Original resume file is not available."
      );
      return;
    }

    setCheckingPhoto(true);
    setEnhanceError("");
    setShowEnhancePhotoOptions(false);

    try {
      const formData =
        new FormData();

      formData.append(
        "job_id",
        resumeJobId
      );

      formData.append(
        "resume_file",
        file
      );

      const response =
        await fetch(
          `${API_URL}/enhance-photo-status`,
          {
            method: "POST",
            body: formData,
          }
        );

      const data =
        await response.json();

      if (
        !response.ok ||
        data.success === false
      ) {
        throw new Error(
          data.message ||
            "Could not check the original resume photo."
        );
      }

      const detected =
        Boolean(
          data.photo_detected
        );

      setOriginalPhotoDetected(
        detected
      );

      if (detected) {
        await createEnhancedResume(
          null
        );
      } else {
        setShowEnhancePhotoOptions(
          true
        );
      }
    } catch (err) {
      setEnhanceError(
        err.message ||
          "Could not check the resume photo."
      );
    } finally {
      setCheckingPhoto(false);
    }
  }

  async function createEnhancedResume(
    photoToSend = null
  ) {
    if (!resumeJobId) {
      setEnhanceError(
        "Please analyze a resume first."
      );
      return;
    }

    if (!file) {
      setEnhanceError(
        "Original resume file is not available."
      );
      return;
    }

    setEnhancing(true);
    setEnhanceError("");

    setEnhancedResume("");
    setEnhancedPdf("");
    setEnhancedFilename("");
    setSelectedEnhanceTemplate("professional");

    try {
      const formData =
        new FormData();

      formData.append(
        "job_id",
        resumeJobId
      );

      formData.append(
        "resume_file",
        file
      );

      if (photoToSend) {
        formData.append(
          "photo",
          photoToSend
        );
      }

      const response =
        await fetch(
          `${API_URL}/enhance`,
          {
            method: "POST",
            body: formData,
          }
        );

      const data =
        await response.json();

      if (
        !response.ok ||
        !data.success
      ) {
        throw new Error(
          data.message ||
            "Resume enhancement failed."
        );
      }

      setEnhancedResume(
        data.enhanced_resume || ""
      );

      setEnhancedPhotoDataUrl(
        data.photo_data_url || ""
      );

      setEnhancedPdf(
        data.pdf_base64 || ""
      );

      setEnhancedFilename(
        data.filename ||
          "ResumeAI-Professional-Resume.pdf"
      );
      setSelectedEnhanceTemplate("professional");

      setShowEnhancePhotoOptions(
        false
      );
    } catch (err) {
      setEnhanceError(
        err.message ||
          "Could not create the professional resume."
      );
    } finally {
      setEnhancing(false);
    }
  }

  async function skipPhotoAndEnhance() {
    setPhoto(null);
    setPhotoPreview("");
    setEnhanceError("");

    await createEnhancedResume(
      null
    );
  }

  async function addPhotoAndEnhance() {
    if (!photo) {
      setEnhanceError(
        "Please choose a JPG or PNG photo first."
      );
      return;
    }

    await createEnhancedResume(
      photo
    );
  }

  async function selectEnhanceTemplate(templateId) {
    if (!resumeJobId || !enhancedResume) {
      setEnhanceError("Please enhance the resume first.");
      return;
    }

    setSelectedEnhanceTemplate(templateId);
    setTemplateGenerating(true);
    setEnhanceError("");

    try {
      const formData = new FormData();
      formData.append("job_id", resumeJobId);
      formData.append("template", templateId);
      formData.append("enhanced_text", enhancedResume);

      const response = await fetch(`${API_URL}/enhance-template`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.message || "Could not create the selected resume style.");
      }

      setEnhancedPdf(data.pdf_base64 || "");
      setEnhancedFilename(data.filename || `ResumeAI-${templateId}-Resume.pdf`);
    } catch (err) {
      setEnhanceError(err.message || "Could not create the selected resume style.");
    } finally {
      setTemplateGenerating(false);
    }
  }

  function downloadEnhancedPDF() {
    if (!enhancedPdf) {
      setEnhanceError(
        "The PDF is not ready yet."
      );
      return;
    }

    try {
      const binary =
        atob(enhancedPdf);

      const bytes =
        new Uint8Array(
          binary.length
        );

      for (
        let i = 0;
        i < binary.length;
        i += 1
      ) {
        bytes[i] =
          binary.charCodeAt(i);
      }

      const blob =
        new Blob(
          [bytes],
          {
            type: "application/pdf",
          }
        );

      const url =
        URL.createObjectURL(
          blob
        );

      const link =
        document.createElement(
          "a"
        );

      link.href = url;

      link.download =
        enhancedFilename ||
        "ResumeAI-Professional-Resume.pdf";

      document.body.appendChild(
        link
      );

      link.click();

      link.remove();

      URL.revokeObjectURL(url);
    } catch {
      setEnhanceError(
        "Could not download the PDF."
      );
    }
  }

  async function sendChatMessage() {
    const message =
      chatInput.trim();

    if (
      !message ||
      !resumeJobId
    ) {
      return;
    }

    setChatInput("");

    setChatMessages(
      (previous) => [
        ...previous,
        {
          role: "user",
          text: message,
        },
      ]
    );

    setChatLoading(true);

    try {
      const response =
        await fetch(
          `${API_URL}/chat`,
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/json",
            },
            body: JSON.stringify({
              job_id: resumeJobId,
              message,
              history: chatMessages.slice(-12),
              page_context: "resume-analysis",
            }),
          }
        );

      const data =
        await response.json();

      if (!data.success) {
        throw new Error(
          data.message ||
            "Chat request failed."
        );
      }

      const chatJobId =
        data.chat_job_id;

      if (!chatJobId) {
        throw new Error(
          "AI chat job was not created."
        );
      }

      for (
        let i = 0;
        i < 80;
        i += 1
      ) {
        const pollResponse =
          await fetch(
            `${API_URL}/chat/${chatJobId}`
          );

        const pollData =
          await pollResponse.json();

        if (
          pollData.status ===
          "completed"
        ) {
          setChatMessages(
            (previous) => [
              ...previous,
              {
                role: "assistant",
                text:
                  pollData.chat_answer ||
                  pollData.answer ||
                  "",
              },
            ]
          );

          break;
        }

        if (
          pollData.status ===
          "failed"
        ) {
          throw new Error(
            pollData.message ||
              "AI chat failed."
          );
        }

        await new Promise(
          (resolve) =>
            setTimeout(
              resolve,
              1200
            )
        );
      }
    } catch (err) {
      setChatMessages(
        (previous) => [
          ...previous,
          {
            role: "assistant",
            text:
              err.message ||
              "Sorry, AI chat failed.",
          },
        ]
      );
    } finally {
      setChatLoading(false);
    }
  }

  function runDashboardSearch(value) {
    const q = String(value || "").trim().toLowerCase();
    if (!q) return;
    const routes = [
      ["resume", ["resume", "analyzer", "analysis", "score", "feedback"]],
      ["jobs", ["job", "jobs", "career", "opportunity", "work"]],
      ["mocks", ["mock", "interview", "practice"]],
      ["applications", ["application", "applications", "applied"]],
      ["profile", ["profile", "account"]],
      ["settings", ["setting", "settings", "theme", "notification"]],
      ["analytics", ["analytics", "stats", "statistics"]],
    ];
    const hit = routes.find(([, words]) => words.some(w => q.includes(w)));
    if (hit) setActivePage(hit[0]);
  }

  function handleChatKeyDown(
    event
  ) {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();
      sendChatMessage();
    }
  }

  async function handleLogin(e) {
    e.preventDefault();
    setAuthLoading(true);
    setAuthMessage("");
    setAuthMessageType("");

    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: loginEmail.trim(),
          password: loginPassword,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Login failed.");
      }

      localStorage.setItem("resumeai_token", data.access_token);
      localStorage.setItem("resumeai_user", JSON.stringify(data.user));

      setCurrentUser(data.user);
      setLoginEmail("");
      setLoginPassword("");
      setAuthMessage("Login successful!");
      setAuthMessageType("success");
      setAccountOpen(false);

      setTimeout(() => {
        setAuthMessage("");
        setAuthMessageType("");
        setActivePage("dashboard");
      }, 500);
    } catch (err) {
      setAuthMessage(err.message || "Unable to login.");
      setAuthMessageType("error");
    } finally {
      setAuthLoading(false);
    }
  }

  async function handleSignup(e) {
    e.preventDefault();
    setAuthLoading(true);
    setAuthMessage("");
    setAuthMessageType("");

    try {
      const response = await fetch(`${API_URL}/auth/signup`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: signupName.trim(),
          email: signupEmail.trim(),
          password: signupPassword,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Account creation failed.");
      }

      localStorage.setItem("resumeai_token", data.access_token);
      localStorage.setItem("resumeai_user", JSON.stringify(data.user));

      setCurrentUser(data.user);
      setSignupName("");
      setSignupEmail("");
      setSignupPassword("");
      setAuthMessage("Account created successfully!");
      setAuthMessageType("success");
      setAccountOpen(false);

      setTimeout(() => {
        setAuthMessage("");
        setAuthMessageType("");
        setActivePage("dashboard");
      }, 500);
    } catch (err) {
      setAuthMessage(err.message || "Unable to create account.");
      setAuthMessageType("error");
    } finally {
      setAuthLoading(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem("resumeai_token");
    localStorage.removeItem("resumeai_user");
    setCurrentUser(null);
    setAccountOpen(false);
    setActivePage("dashboard");
  }

  function resetApp() {
    setActivePage("resume");
    setFile(null);

    setPhoto(null);
    setPhotoPreview("");

    setResult(null);
    setError("");

    setAiAdvice(null);
    setAiStatus("");

    setChatMessages([]);
    setChatInput("");

    setEnhancedResume("");
    setEnhancedPdf("");
    setEnhancedFilename("");
    setSelectedEnhanceTemplate("professional");
    setEnhanceError("");

    setShowEnhancePhotoOptions(
      false
    );

    setCheckingPhoto(false);
    setOriginalPhotoDetected(null);

    setShowScoreDetails(false);
  }

  function DashboardHome() {
    const analyzed = Boolean(result);
    const bd = result?.breakdown || {};
    const sectionScore = (key) => {
      const raw = Number(bd[key]);
      if (!Number.isFinite(raw)) return null;
      return Math.max(0, Math.min(100, Math.round((raw / 15) * 100)));
    };
    const summaryScore = sectionScore("summary");
    const skillsScore = sectionScore("skills");
    const experienceScore = sectionScore("experience");
    const educationScore = sectionScore("education");
    const suggestionCount = Array.isArray(suggestions) ? suggestions.length : 0;
    const strongPoints = Array.isArray(strengths) ? strengths.length : 0;
    const matchPotential = score >= 85 ? "High" : score >= 70 ? "Medium" : "Needs work";
    const sectionRows = [
      ["🎯", "Overall Score", analyzed ? `${score}/100` : "—", analyzed ? "Score" : "Analyze first"],
      ["📄", "Summary", summaryScore != null ? `${summaryScore}/100` : "—", summaryScore >= 80 ? "Good" : "Improve"],
      ["🧩", "Skills Analysis", skillsScore != null ? `${skillsScore}/100` : "—", skillsScore >= 80 ? "Strong" : "Improve"],
      ["💼", "Experience", experienceScore != null ? `${experienceScore}/100` : "—", experienceScore >= 80 ? "Good" : "Improve"],
      ["🎓", "Education", educationScore != null ? `${educationScore}/100` : "—", educationScore >= 80 ? "Good" : "Improve"],
      ["💡", "Suggestions", analyzed ? `${suggestionCount} areas` : "—", "Review"],
    ];

    return (
      <main className="workspace-page dashboard-reference-page">
        <div className="dashboard-topline">
          <div className="dashboard-search"><span>⌕</span><input placeholder="Search anything..." aria-label="Search anything" onKeyDown={e => { if (e.key === "Enter") runDashboardSearch(e.currentTarget.value); }} /></div>
          <div className="dashboard-user"><span className="dashboard-notification">🔔</span><span className="dashboard-user-avatar">{(currentUser?.name || "U").slice(0,1).toUpperCase()}</span><strong>{currentUser?.name || "User"}</strong><span>⌄</span></div>
        </div>

        <div className="dashboard-reference-grid">
          <section className="dashboard-hero-card">
            <div className="dashboard-crown">♛</div>
            <div className={`dashboard-score-orbit ${analyzed ? scoreInfo.className : "empty"}`}>
              <div className="dashboard-score-orbit-inner">
                <strong>{analyzed ? score : "—"}</strong>
                <span>/ 100</span>
              </div>
            </div>
            <div className="dashboard-hero-emoji">{analyzed ? scoreInfo.emoji : "✨"}</div>
            <h1>{analyzed ? (score >= 80 ? "Great Resume!" : score >= 65 ? "Good Start!" : "Let's Improve It!") : "Your Resume Journey Starts Here"}</h1>
            <p>{analyzed ? (result.verdict_message || scoreInfo.message) : "Analyze your resume to get a clear score, practical insights and personalized next steps."}</p>

            <div className="dashboard-insight-row">
              <div><span>✓</span><small>Strong Points</small><strong>{analyzed ? strongPoints : "—"}</strong></div>
              <div><span>💡</span><small>Areas to Improve</small><strong>{analyzed ? suggestionCount : "—"}</strong></div>
              <div><span>★</span><small>ATS Friendly</small><strong>{analyzed ? (Number(bd.ats || 0) >= 8 ? "Yes" : "Improve") : "—"}</strong></div>
              <div><span>🎯</span><small>Match Potential</small><strong>{analyzed ? matchPotential : "—"}</strong></div>
            </div>

            {analyzed && suggestions[0] ? (
              <div className="dashboard-quick-tip"><span>💡</span><div><strong>Quick Tip</strong><p>{suggestions[0]}</p></div></div>
            ) : (
              <div className="dashboard-quick-tip"><span>💡</span><div><strong>Quick Tip</strong><p>Use measurable achievements and clear section headings when your resume supports them.</p></div></div>
            )}

            <div className="dashboard-hero-actions">
              <button className="workspace-primary" onClick={() => setActivePage("resume")}>{analyzed ? "↻ Analyze Another" : "↑ Analyze Resume"}</button>
              {analyzed && <button className="dashboard-outline-btn" onClick={() => setActivePage("resume")}>View Full Report →</button>}
            </div>
          </section>

          <aside className="dashboard-side-column">
            <section className="dashboard-side-card">
              <div className="dashboard-side-title"><h2>Resume Analysis</h2><span>›</span></div>
              {sectionRows.map(([icon, label, value, status]) => (
                <button className="dashboard-analysis-row" key={label} onClick={() => setActivePage("resume")}>
                  <span className="dashboard-row-icon">{icon}</span><span className="dashboard-row-label">{label}</span><strong className={status === "Strong" || status === "Good" ? "positive" : status === "Improve" ? "warning" : ""}>{value}</strong><em>{status}</em><span>›</span>
                </button>
              ))}
            </section>

            <section className="dashboard-side-card next-steps-card">
              <div className="dashboard-side-title"><h2>Next Steps</h2><span>🚀</span></div>
              {(suggestions.length ? suggestions.slice(0, 3) : ["Analyze a resume to generate personalized next steps.", "Review your resume score and section feedback.", "Use AI Career Advisor for career guidance."]).map((item, i) => (
                <div className="dashboard-next-step" key={i}><span>✓</span><p>{item}</p></div>
              ))}

            </section>
          </aside>
        </div>

        <section className="dashboard-bottom-banner"><span>✨</span><strong>Your journey to a better career is just getting started!</strong><span>Keep going! ↗</span></section>
      </main>
    );
  }

  if (siteLocked) {
    return (
      <div className="site-lock-screen">
        <div className="site-lock-card">
          <div className="site-lock-icon">🔐</div>
          <span className="eyebrow">RESUMEAI SECURITY</span>
          <h1>Workspace Locked</h1>
          <p>Enter the PIN you created in Settings → Security to continue.</p>
          <input autoFocus type="password" inputMode="numeric" maxLength="12" value={lockPin} onChange={e => setLockPin(e.target.value.replace(/\D/g, ""))} onKeyDown={e => { if (e.key === "Enter") unlockSite(); }} placeholder="Enter your PIN" />
          <button className="workspace-primary" onClick={unlockSite} disabled={lockPin.length < 4}>Unlock ResumeAI</button>
          {lockMessage && <p className="lock-error">{lockMessage}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell workspace-shell">
      <header className="workspace-topbar">
        <button className="workspace-brand" onClick={() => setActivePage("dashboard")}><span className="workspace-brand-logo">🤖</span><span><b>Resume<span>AI</span></b><small>Career Intelligence</small></span></button>
        <nav className="workspace-topnav"><button className={activePage === "dashboard" ? "active" : ""} onClick={() => setActivePage("dashboard")}>⌂ Dashboard</button><button className={activePage === "mocks" ? "active" : ""} onClick={() => setActivePage("mocks")}>▣ Mocks</button><button className={activePage === "jobs" ? "active" : ""} onClick={() => setActivePage("jobs")}>▣ Jobs</button><button className={activePage === "resources" ? "active" : ""} onClick={() => setActivePage("resources")}>▤ Resources</button><button className={activePage === "analytics" ? "active" : ""} onClick={() => setActivePage("analytics")}>⌁ Analytics</button></nav>
        <div className="workspace-notification-wrap">
          <button className="workspace-notification-btn" onClick={() => setNotificationOpen(v => !v)} aria-label="Notifications">🔔{notifications.some(n => !n.read) && <i>{notifications.filter(n => !n.read).length > 9 ? "9+" : notifications.filter(n => !n.read).length}</i>}</button>
          {notificationOpen && <div className="workspace-notification-menu"><div className="notification-menu-head"><strong>Notifications</strong><button type="button" onClick={async () => { await fetch(`${API_URL}/api/notifications/read-all`, { method: "POST", headers: apiAuthHeaders() }); setNotifications(prev => prev.map(n => ({...n,read:1}))); }}>Mark all read</button></div>{notifications.length ? notifications.slice(0,8).map(n => <button className={`notification-item ${n.read ? "read" : "unread"}`} key={n.id} onClick={() => markNotificationRead(n.id)}><strong>{n.title}</strong><span>{n.body}</span><small>{new Date(n.created_at).toLocaleString()}</small></button>) : <div className="notification-empty">No notifications yet.</div>}</div>}
        </div>
        <div className="workspace-account-wrap">
          <button className="workspace-account" onClick={() => setAccountOpen(!accountOpen)}>
            <span className="workspace-avatar workspace-avatar-image">{globalProfilePhoto ? <img src={globalProfilePhoto} alt=""/> : "👤"}</span>
            <span>{currentUser ? currentUser.name : "Login / Sign Up"}</span>
            <span>⌄</span>
          </button>
          {accountOpen && (
            <div className="workspace-account-menu">
              {currentUser ? (
                <>
                  <button onClick={() => { setAccountOpen(false); setActivePage("profile"); }}>👤 My Profile</button>
                  <button onClick={() => { setAccountOpen(false); setActivePage("premium"); }}>👑 ResumeAI Premium — 🚀 Coming Soon</button>
                  <button onClick={handleLogout}>⇥ Logout</button>
                </>
              ) : (
                <>
                  <button onClick={() => { setAccountOpen(false); setAuthMessage(""); setActivePage("login"); }}>⇥ Login</button>
                  <button onClick={() => { setAccountOpen(false); setAuthMessage(""); setActivePage("signup"); }}>＋ Create Account</button>
                </>
              )}
            </div>
          )}
        </div>
      </header>
      <aside className="workspace-sidebar"><div className="workspace-brand-mini"><span className="workspace-brand-robot">🤖</span><div><b>ResumeAI</b><small>AI Career Intelligence</small></div></div><div className="workspace-side-label">WORKSPACE</div><button className={activePage === "dashboard" ? "active" : ""} onClick={() => setActivePage("dashboard")}>🏠 <span>Dashboard</span></button><button className={activePage === "resume" ? "active" : ""} onClick={() => setActivePage("resume")}>📄 <span>Resume Analyzer</span></button><button className={activePage === "mocks" ? "active" : ""} onClick={() => setActivePage("mocks")}>🎤 <span>Mocks</span></button><button className={activePage === "jobs" ? "active" : ""} onClick={() => setActivePage("jobs")}>💼 <span>Jobs</span></button><button className={activePage === "applications" ? "active" : ""} onClick={() => setActivePage("applications")}>📋 <span>My Applications</span></button><button className={activePage === "profile" ? "active" : ""} onClick={() => setActivePage("profile")}>👤 <span>Profile</span></button><button className={activePage === "settings" ? "active" : ""} onClick={() => setActivePage("settings")}>⚙️ <span>Settings</span></button><div className="workspace-side-footer"><b>ResumeAI</b><span>Build Better Resumes.<br/>Get Better Jobs.</span></div></aside>
      <div className="workspace-content">
        {activePage === "dashboard" && <DashboardHome />}
        {activePage === "mocks" && <WorkspaceModules page="mocks" currentUser={currentUser} onNavigate={setActivePage} resumeJobId={resumeJobId} onLogout={handleLogout} />}
        {activePage === "jobs" && <WorkspaceModules page="jobs" currentUser={currentUser} onNavigate={setActivePage} resumeJobId={resumeJobId} onLogout={handleLogout} />}
        {activePage === "applications" && <WorkspaceModules page="applications" currentUser={currentUser} onNavigate={setActivePage} resumeJobId={resumeJobId} onLogout={handleLogout} />}
        {activePage === "resources" && <SimplePage title="Resources" icon="📚" description="Career resources from ResumeAI."><div className="workspace-module"><h2>Career Resources</h2><p>Resume writing, interview preparation and job-search guidance will be added here.</p></div></SimplePage>}
        {activePage === "analytics" && <WorkspaceModules page="analytics" currentUser={currentUser} onNavigate={setActivePage} resumeJobId={resumeJobId} onLogout={handleLogout} />}
        {activePage === "profile" && <WorkspaceModules page="profile" currentUser={currentUser} onNavigate={setActivePage} resumeJobId={resumeJobId} onLogout={handleLogout} />}
        {activePage === "settings" && <WorkspaceModules page="settings" currentUser={currentUser} onNavigate={setActivePage} resumeJobId={resumeJobId} onLogout={handleLogout} />}
        {activePage === "login" && (
          <SimplePage title="Login" icon="🔐" description="Sign in to your ResumeAI account.">
            <form className="workspace-auth" onSubmit={handleLogin}>
              <h2>Login</h2>
              <button type="button" className="google-login-btn" onClick={() => { window.location.href = `${API_URL}/auth/google/start`; }}>Continue with Google</button><div className="auth-divider"><span>or</span></div>
              <input
                placeholder="Email"
                type="email"
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                required
              />
              <input
                placeholder="Password"
                type="password"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                required
              />
              {authMessage && (
                <p style={{ color: authMessageType === "error" ? "#dc2626" : "#15803d", fontWeight: 600 }}>
                  {authMessage}
                </p>
              )}
              <button className="workspace-primary" type="submit" disabled={authLoading}>
                {authLoading ? "Logging in..." : "Login"}
              </button>
              <p>
                Don't have an account? {" "}
                <button type="button" onClick={() => { setAuthMessage(""); setActivePage("signup"); }}>
                  Create Account
                </button>
              </p>
            </form>
          </SimplePage>
        )}
        {activePage === "signup" && (
          <SimplePage title="Create Account" icon="✨" description="Create your ResumeAI account.">
            <form className="workspace-auth" onSubmit={handleSignup}>
              <h2>Create Account</h2>
              <button type="button" className="google-login-btn" onClick={() => { window.location.href = `${API_URL}/auth/google/start`; }}>Continue with Google</button><div className="auth-divider"><span>or</span></div>
              <input
                placeholder="Name"
                value={signupName}
                onChange={(e) => setSignupName(e.target.value)}
                required
              />
              <input
                placeholder="Email"
                type="email"
                value={signupEmail}
                onChange={(e) => setSignupEmail(e.target.value)}
                required
              />
              <input
                placeholder="Password (minimum 6 characters)"
                type="password"
                value={signupPassword}
                onChange={(e) => setSignupPassword(e.target.value)}
                minLength={6}
                required
              />
              {authMessage && (
                <p style={{ color: authMessageType === "error" ? "#dc2626" : "#15803d", fontWeight: 600 }}>
                  {authMessage}
                </p>
              )}
              <button className="workspace-primary" type="submit" disabled={authLoading}>
                {authLoading ? "Creating Account..." : "Create Account"}
              </button>
              <p>
                Already have an account? {" "}
                <button type="button" onClick={() => { setAuthMessage(""); setActivePage("login"); }}>
                  Login
                </button>
              </p>
            </form>
          </SimplePage>
        )}
        {activePage === "premium" && <WorkspaceModules page="premium" currentUser={currentUser} onNavigate={setActivePage} resumeJobId={resumeJobId} onLogout={handleLogout} />}
        {activePage === "resume" && <div className="workspace-resume-content">
      <header className="topbar">
        <div className="brand">
          <div className="brand-logo">
            R
          </div>

          <div>
            <div className="brand-name">
              ResumeAI
            </div>

            <div className="brand-subtitle">
              AI Resume Analyzer
            </div>
          </div>
        </div>

        {result && (
          <button
            className="reset-button"
            onClick={resetApp}
          >
            New Resume
          </button>
        )}
      </header>

      {!result && (
        <main className="hero-section">
          <div className="hero-content">
            <div className="hero-badge">
              AI-POWERED RESUME ANALYZER
            </div>

            <h1>
              Make Your Resume
              <br />
              <span>Job Ready.</span>
            </h1>

            <p>
              Upload your resume and get an
              honest AI-powered analysis,
              actionable improvements and
              career guidance.
            </p>
          </div>

          <div className="upload-card">
            <div className="upload-icon">
              ↑
            </div>

            <h2>
              Upload Your Resume
            </h2>

            <p>
              PDF, DOCX, JPG, JPEG, PNG, WEBP or TXT
            </p>

            <label className="upload-button">
              Choose Resume

              <input
                type="file"
                accept=".pdf,.doc,.docx,.rtf,.odt,.jpg,.jpeg,.png,.webp,.txt"
                onChange={
                  handleFileChange
                }
                hidden
              />
            </label>

            {file && (
              <div className="selected-file">
                <strong>
                  Selected:
                </strong>{" "}
                {file.name}
              </div>
            )}

            <button
              className="analyze-button"
              onClick={
                analyzeResume
              }
              disabled={
                loading || !file
              }
            >
              {loading
                ? "Analyzing..."
                : "Analyze Resume →"}
            </button>

            {error && (
              <div className="error-message">
                {error}
              </div>
            )}
          </div>
        </main>
      )}

      {result && (
        <main className="dashboard">
          <div className="dashboard-header">
            <div>
              <div className="hero-badge">
                ANALYSIS COMPLETE
              </div>

              <h1>
                Your Resume Report
              </h1>

              <p>
                Honest analysis based on the
                content detected in your resume.
              </p>
            </div>
          </div>

          {/* SCORE + OVERVIEW */}

          <div className="dashboard-grid">
            <section className={`score-card score-card-modern ${scoreInfo.className}`}>
              <div className="score-card-topline"><span className="score-title-icon">🎯</span><span className="score-label">RESUME HEALTH</span><span className="score-verified">✓ ANALYZED</span></div>
              <div className="score-orbit-modern">
                <div className="score-orbit-glow"></div>
                <div className="score-orbit-inner">
                  <span className="score-mini-label">OVERALL SCORE</span>
                  <strong>{score}</strong><span className="score-out-of">/ 100</span>
                </div>
              </div>
              <div className="score-mood-row"><span className="score-mood-emoji">{scoreInfo.emoji}</span><div><h2>{scoreInfo.label}</h2><p>{result.verdict_message || scoreInfo.message}</p></div></div>
              <div className="score-scale"><span>Needs work</span><div><i style={{width:`${Math.max(4,Math.min(100,score))}%`}}></i></div><span>Job ready</span></div>
              <button type="button" className="details-button score-details-button" onClick={() => setShowScoreDetails(!showScoreDetails)}>{showScoreDetails ? "Hide Score Details ↑" : "View Score Details ↓"}</button>
              {showScoreDetails && <div className="why-score why-score-modern"><h3>✨ Why this score?</h3>{Array.isArray(result.why_score) && result.why_score.length > 0 ? <ul>{result.why_score.map((item,index)=><li key={index}><span>{index+1}</span>{item}</li>)}</ul> : <p className="muted">Your score reflects resume structure, content quality, evidence and ATS-related factors detected in the uploaded resume.</p>}</div>}
            </section>

            <section className="overview-card">
              <div className="card-heading">
                <span>📋</span>
                Resume Overview
              </div>

              <div className="section-status-list">
                {SECTION_LIST.map(
                  ([key, label]) => {
                    const present =
                      detectedSections.includes(
                        key
                      );

                    return (
                      <div
                        className="section-status"
                        key={key}
                      >
                        <span>
                          {label}
                        </span>

                        <span
                          className={
                            present
                              ? "status-present"
                              : "status-missing"
                          }
                        >
                          {present
                            ? "✓ Present"
                            : "✕ Missing"}
                        </span>
                      </div>
                    );
                  }
                )}
              </div>
            </section>
          </div>

          {/* QUICK INSIGHTS */}

          <section className="report-card">
            <div className="card-heading">
              <span>💡</span>
              Quick Resume Insights
            </div>

            <div className="analysis-grid">
              <div className="analysis-box">
                <h3>
                  📄 Resume Length
                </h3>

                <p className="insight-value">
                  {result.word_count ||
                    0}{" "}
                  words
                </p>

                <p className="muted">
                  Resume content detected by
                  ResumeAI.
                </p>
              </div>

              <div className="analysis-box">
                <h3>
                  🛠️ Technical Skills
                </h3>

                <p className="insight-value">
                  {skills.length}
                </p>

                <p className="muted">
                  Recognizable technical skills
                  detected.
                </p>
              </div>

              <div className="analysis-box">
                <h3>
                  📌 Resume Sections
                </h3>

                <p className="insight-value">
                  {detectedSections.length}
                </p>

                <p className="muted">
                  Resume sections detected
                  successfully.
                </p>
              </div>

              <div className="analysis-box">
                <h3>
                  📈 Measurable Evidence
                </h3>

                <p className="insight-value">
                  {Array.isArray(
                    result.metrics_found
                  )
                    ? result.metrics_found
                        .length
                    : 0}
                </p>

                <p className="muted">
                  Metrics and measurable evidence
                  found.
                </p>
              </div>
            </div>
          </section>

          {/* SCORE BREAKDOWN */}

          <section className="report-card">
            <div className="card-heading">
              <span>📊</span>
              Score Breakdown
            </div>

            <div className="breakdown-grid">
              {Object.entries(
                breakdown
              ).map(
                ([key, value]) => (
                  <div
                    className="breakdown-item"
                    key={key}
                  >
                    <div>
                      {key
                        .replace(
                          /_/g,
                          " "
                        )
                        .replace(
                          /\b\w/g,
                          (char) =>
                            char.toUpperCase()
                        )}
                    </div>

                    <strong>
                      {value}
                    </strong>
                  </div>
                )
              )}
            </div>
          </section>

          {/* CONTENT ANALYSIS */}

          <section className="report-card">
            <div className="card-heading">
              <span>✨</span>
              Content Analysis
            </div>

            <div className="analysis-grid">
              <div className="analysis-box">
                <h3>
                  ✅ Strengths
                </h3>

                {strengths.length >
                0 ? (
                  <ul>
                    {strengths.map(
                      (
                        item,
                        index
                      ) => (
                        <li
                          key={index}
                        >
                          {item}
                        </li>
                      )
                    )}
                  </ul>
                ) : (
                  <p className="muted">
                    No major strengths were
                    detected yet.
                  </p>
                )}
              </div>

              <div className="analysis-box">
                <h3>
                  ⚠️ Improvements
                </h3>

                {suggestions.length >
                0 ? (
                  <ul>
                    {suggestions.map(
                      (
                        item,
                        index
                      ) => (
                        <li
                          key={index}
                        >
                          {item}
                        </li>
                      )
                    )}
                  </ul>
                ) : (
                  <p className="muted">
                    No major improvements
                    detected.
                  </p>
                )}
              </div>
            </div>
          </section>

          {/* SKILLS */}

          <section className="report-card">
            <div className="card-heading">
              <span>🛠️</span>
              Detected Skills
            </div>

            <div className="skills-list">
              {skills.length >
              0 ? (
                skills.map(
                  (
                    skill,
                    index
                  ) => (
                    <span
                      className="skill-chip"
                      key={index}
                    >
                      {skill}
                    </span>
                  )
                )
              ) : (
                <p className="muted">
                  No recognizable technical
                  skills were detected.
                </p>
              )}
            </div>
          </section>

          {/* AI ADVISOR */}

          <section id="ai-advisor-section" className="report-card ai-advisor">
            <div className="card-heading">
              <span>🤖</span>
              AI Career Advisor
            </div>

            <p className="muted">
              Personalized AI feedback based
              only on the information found in
              your resume.
            </p>

            {aiStatus ===
              "processing" && (
              <div className="ai-loading">
                🤖 AI is reviewing your resume...
              </div>
            )}

            {aiAdvice &&
              aiAdvice.success && (
                <div className="feedback-content">
                  <div className="feedback-block">
                    <h3>
                      Overall Advice
                    </h3>

                    <p>
                      {aiAdvice.overall_advice}
                    </p>
                  </div>

                  {aiAdvice.high_priority_issues
                    ?.length >
                    0 && (
                    <div className="feedback-block">
                      <h3>
                        🔥 High Priority
                      </h3>

                      <ul>
                        {aiAdvice.high_priority_issues.map(
                          (
                            item,
                            index
                          ) => (
                            <li
                              key={
                                index
                              }
                            >
                              {item}
                            </li>
                          )
                        )}
                      </ul>
                    </div>
                  )}

                  {aiAdvice.medium_priority_issues
                    ?.length >
                    0 && (
                    <div className="feedback-block">
                      <h3>
                        🟡 Medium Priority
                      </h3>

                      <ul>
                        {aiAdvice.medium_priority_issues.map(
                          (
                            item,
                            index
                          ) => (
                            <li
                              key={
                                index
                              }
                            >
                              {item}
                            </li>
                          )
                        )}
                      </ul>
                    </div>
                  )}

                  {aiAdvice.strengths
                    ?.length >
                    0 && (
                    <div className="feedback-block">
                      <h3>
                        🟢 Strengths
                      </h3>

                      <ul>
                        {aiAdvice.strengths.map(
                          (
                            item,
                            index
                          ) => (
                            <li
                              key={
                                index
                              }
                            >
                              {item}
                            </li>
                          )
                        )}
                      </ul>
                    </div>
                  )}

                  {aiAdvice.actionable_suggestions
                    ?.length >
                    0 && (
                    <div className="feedback-block">
                      <h3>
                        🎯 Actionable Suggestions
                      </h3>

                      <ul>
                        {aiAdvice.actionable_suggestions.map(
                          (
                            item,
                            index
                          ) => (
                            <li
                              key={
                                index
                              }
                            >
                              {item}
                            </li>
                          )
                        )}
                      </ul>
                    </div>
                  )}
                </div>
              )}

            {aiStatus ===
              "failed" && (
              <p className="muted">
                AI advisor could not complete
                right now. Your rule-based report
                is still available.
              </p>
            )}
          </section>

          {/* AI CHAT */}

          <section id="ai-chat-section" className="report-card">
            <div className="card-heading">
              <span>💬</span>
              AI Career Chat
            </div>

            <p className="muted">
              Ask anything about this resume in
              English, Hindi or Hinglish.
            </p>

            <div className="chat-box">
              <div className="chat-messages">
                {chatMessages.length ===
                  0 && (
                  <div className="chat-empty">
                    💬 Ask your first question
                    about the resume.
                  </div>
                )}

                {chatMessages.map(
                  (
                    message,
                    index
                  ) => (
                    <div
                      className={`chat-message ${message.role}`}
                      key={index}
                    >
                      <div className="chat-role">
                        {message.role ===
                        "user"
                          ? "You"
                          : "ResumeAI"}
                      </div>

                      <div className="chat-text">
                        {message.text}
                      </div>
                    </div>
                  )
                )}

                {chatLoading && (
                  <div className="chat-message assistant">
                    <div className="chat-role">
                      ResumeAI
                    </div>

                    <div className="chat-text">
                      🤖 Thinking...
                    </div>
                  </div>
                )}
              </div>

              <div className="chat-input-row">
                <textarea
                  value={chatInput}
                  onChange={(event) =>
                    setChatInput(
                      event.target.value
                    )
                  }
                  onKeyDown={
                    handleChatKeyDown
                  }
                  placeholder="Ask about your resume..."
                  rows={2}
                  disabled={
                    chatLoading
                  }
                />

                <button
                  onClick={
                    sendChatMessage
                  }
                  disabled={
                    chatLoading ||
                    !chatInput.trim()
                  }
                >
                  Send
                </button>
              </div>
            </div>
          </section>

          {/* ACTION PLAN */}

          <section className="report-card">
            <div className="card-heading">
              <span>🎯</span>
              Action Plan
            </div>

            {actionPlan.length >
            0 ? (
              <div className="action-plan">
                {actionPlan.map(
                  (
                    item,
                    index
                  ) => (
                    <div
                      className="action-item"
                      key={index}
                    >
                      <div className="action-number">
                        {index + 1}
                      </div>

                      <div>
                        {item}
                      </div>
                    </div>
                  )
                )}
              </div>
            ) : (
              <p className="muted">
                No action items available.
              </p>
            )}
          </section>

          {/* ENHANCE RESUME */}

          <section id="enhance-resume-section" className="report-card enhance-card">
            <div className="card-heading">
              <span>✨</span>
              Enhance My Resume
            </div>

            <div className="enhance-content">
              <div>
                <h2>
                  Build a more professional
                  resume
                </h2>

                <p>
                  ResumeAI will improve wording,
                  structure and presentation
                  while keeping the factual
                  information from your original
                  resume.
                </p>

                <div className="enhance-features">
                  <span>
                    ✓ Professional formatting
                  </span>

                  <span>
                    ✓ ATS-friendly structure
                  </span>

                  <span>
                    ✓ Stronger wording
                  </span>

                  <span>
                    ✓ Clean bullet points
                  </span>

                  <span>
                    ✓ Original facts preserved
                  </span>

                  <span>
                    ✓ Photo preserved when
                    available
                  </span>
                </div>
              </div>

              {!showEnhancePhotoOptions &&
                !enhancedResume && (
                  <button
                    className="enhance-button"
                    onClick={
                      handleEnhanceClick
                    }
                    disabled={
                      enhancing ||
                      checkingPhoto
                    }
                  >
                    {checkingPhoto
                      ? "Checking Resume..."
                      : enhancing
                        ? "Creating Resume..."
                        : "Enhance Resume →"}
                  </button>
                )}
            </div>

            {originalPhotoDetected ===
              true &&
              enhancing && (
                <div className="enhance-info">
                  📷 Profile photo detected in
                  your original resume. It will
                  be preserved automatically.
                </div>
              )}

            {showEnhancePhotoOptions &&
              !enhancedResume && (
                <div className="enhance-photo-options">
                  <div className="enhance-photo-header">
                    <h3>
                      Profile Photo
                      <span>
                        {" "}
                        (Optional)
                      </span>
                    </h3>

                    <p>
                      No profile photo was detected
                      in your original resume. You
                      can add one or continue without
                      a photo.
                    </p>
                  </div>

                  <div className="enhance-photo-actions">
                    <label className="photo-button">
                      {photo
                        ? "Change Photo"
                        : "Add Photo"}

                      <input
                        type="file"
                        accept=".jpg,.jpeg,.png"
                        onChange={
                          handlePhotoChange
                        }
                        hidden
                      />
                    </label>

                    <button
                      type="button"
                      className="enhance-button"
                      onClick={
                        skipPhotoAndEnhance
                      }
                      disabled={
                        enhancing
                      }
                    >
                      {enhancing
                        ? "Creating PDF..."
                        : "Skip Photo & Enhance"}
                    </button>
                  </div>

                  {photoPreview && (
                    <div className="photo-preview-wrap">
                      <img
                        src={photoPreview}
                        alt="Selected profile preview"
                        className="photo-preview"
                      />

                      <button
                        type="button"
                        className="enhance-button"
                        onClick={
                          addPhotoAndEnhance
                        }
                        disabled={
                          enhancing
                        }
                      >
                        {enhancing
                          ? "Creating PDF..."
                          : "Create Enhanced Resume"}
                      </button>
                    </div>
                  )}
                </div>
              )}

            {enhanceError && (
              <div className="enhance-error">
                {enhanceError}
              </div>
            )}

            {enhancedResume && (
              <div className="enhanced-result">
                <div className="enhanced-result-header">
                  <div>
                    <h3>✨ Choose Your Resume Style</h3>
                    <p>Pick a design first. The selected version can then be downloaded as a PDF.</p>
                  </div>
                  <button
                    className="download-button"
                    onClick={downloadEnhancedPDF}
                    disabled={!enhancedPdf || templateGenerating}
                  >
                    {templateGenerating ? "Preparing PDF..." : "⬇ Download Selected PDF"}
                  </button>
                </div>

                <div className="enhance-template-grid">
                  {[
                    { id: "professional", name: "Professional", tag: "Existing ResumeAI Style", icon: "▤" },
                    { id: "executive", name: "Executive Two-Column", tag: "Inspired by your sample", icon: "▥" },
                    { id: "modern", name: "Modern Sidebar", tag: "Bold & structured", icon: "◈" },
                    { id: "minimal", name: "Minimal ATS", tag: "Clean & recruiter-friendly", icon: "≡" },
                  ].map((template) => (
                    <button
                      type="button"
                      key={template.id}
                      className={`enhance-template-card ${selectedEnhanceTemplate === template.id ? "selected" : ""}`}
                      onClick={() => selectEnhanceTemplate(template.id)}
                      disabled={templateGenerating}
                    >
                      <div className={`template-thumb template-thumb-${template.id}`}>
                        <div className="template-thumb-top">
                          <span>{template.icon}</span>
                          <b>{template.id === "executive" ? "MATTHEW" : "RESUME"}</b>
                        </div>
                        <div className="template-thumb-body">
                          <i></i><i></i><i></i><i></i><i></i>
                        </div>
                      </div>
                      <div className="template-card-text">
                        <strong>{template.name}</strong>
                        <span>{template.tag}</span>
                      </div>
                      <span className="template-select-state">{selectedEnhanceTemplate === template.id ? "✓ Selected" : "Select"}</span>
                    </button>
                  ))}
                </div>

                <div className="selected-template-label">
                  Preview: <strong>{selectedEnhanceTemplate === "professional" ? "Professional" : selectedEnhanceTemplate === "executive" ? "Executive Two-Column" : selectedEnhanceTemplate === "modern" ? "Modern Sidebar" : "Minimal ATS"}</strong>
                </div>

                <div className="resume-paper">
                  {renderEnhancedPreview(
                    enhancedResume,
                    enhancedPhotoDataUrl,
                    selectedEnhanceTemplate
                  )}
                </div>
              </div>
            )}
          </section>
        </main>
      )}
      </div>}
      </div>
    </div>
  );
}

export default App;
