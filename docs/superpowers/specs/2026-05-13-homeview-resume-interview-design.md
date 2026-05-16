# HomeView + Resume-Driven Interview Flow

## Date
2026-05-13

## Summary
Add a HomeView as the new landing page. Left sidebar shows resume list + import; right area shows resume info and a "模拟面试" (Mock Interview) button. Clicking it navigates to the existing VideoChat/WSVideoChat interview interface.

## Motivation
Current app goes straight to webcam permission gate → interview, with resume upload buried inside the interview view. Users need a dedicated home page to manage resumes and explicitly start interviews.

## Architecture

```
App.vue
├── appMode === 'home'  →  HomeView.vue       (NEW)
│   ├── Left: ResumePanel with list + import
│   └── Right: ResumeInfo card + "模拟面试" button
│
└── appMode === 'interview'  →  existing flow  (NO CHANGES)
```

## Components

### HomeView.vue (NEW)
- Left sidebar (~300px, purple glassmorphism, matching existing gradient)
  - "简历管理" header
  - Resume list (cards: filename, upload date, tags)
  - "导入简历" button → opens modal reusing ResumeUpload logic
- Right main area (white background)
  - No resume selected: placeholder text
  - Resume selected: info card + large purple "模拟面试" button
  - Click "模拟面试" → set appMode='interview', carry resume data to chat store

### Store Changes (store/app.ts)
- Add `appMode: 'home' | 'interview'` (default `'home'`)
- Add `selectedResume / resumeList` state
- Action `startInterview()` to switch mode

### App.vue (MODIFIED)
- Wrap in conditional: `appMode === 'home'` render HomeView, else render current template
- Existing webcam permission flow left untouched

### favicon (FIX)
- Generate or place favicon.ico to resolve 404

## Data Flow
1. User lands on HomeView
2. User imports resume(s) → uploaded to server, question generation triggered
3. User selects a resume → shows resume info on right
4. User clicks "模拟面试" → appMode='interview' → existing WebcamPermission → VideoChat/WSVideoChat
5. Resume context carried into interview via store

## Non-goals
- No changes to VideoChat, WSVideoChat, or WebRTC handling
- No changes to Manager dashboard
- No vue-router (keep simple store-based switching)
