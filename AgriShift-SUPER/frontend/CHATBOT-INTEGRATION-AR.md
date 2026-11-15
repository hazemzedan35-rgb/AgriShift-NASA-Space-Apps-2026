# AgriShift Floating Chat — Integration Handoff

## What was added

A persistent, mobile-responsive floating chat launcher and panel appear on **both** `index.html` and `dashboard.html`. The design uses the existing AgriShift palette and mark, with no third-party UI libraries. It does not change any existing agricultural analysis API calls.

**Important:** The supplied ZIP did **not** include the new chatbot code or its endpoint. As a result, the chat UI runs in a transparent **connection pending** state. It does not invent answers. You must connect your actual chatbot backend for replies.

## Where to configure

Edit **`dist/js/agrishift-chat-config.js`**. Change only the endpoint to the real route supplied by the backend developer, for example:

```js
window.AGRISHIFT_CHAT_CONFIG = {
  endpoint: '/api/your-real-chat-route', // REPLACE with your actual API endpoint
  timeoutMs: 25000,
  createPayload: ({message, history, page}) => ({message, history, page}),
  getReply: (data) => data.reply
};
```

This is a **sample**, not a claim that such an endpoint exists. If your backend expects a different JSON request or response, adjust `createPayload` / `getReply` to match.

### Default expected request (POST JSON)

```json
{
  "message": "How can I compare crops?",
  "history": [{"role": "user", "content": "Hello"}],
  "page": "/dashboard.html#farm"
}
```

### Default expected response

```json
{"reply": "Your chatbot's real answer goes here."}
```

`getReply` also supports common fields `answer`, `response`, `message`, `text`, `data.reply`, `data.answer`, or `choices[0].message.content`. For streaming responses (SSE) or a conversation-ID-based backend, the adapter needs further adjustment after the real API specification is provided.

**Security:** Keep model tokens, secret API keys and third-party service credentials **server-side**. Use a same-origin backend route/proxy, not a secret key embedded in this frontend. Apply server-side rate limiting and input validation.

## UX and behavior

- Round floating button at bottom-right on both pages, visible during regular scrolling.
- Opens a chat panel with an AgriShift mark, welcome message, three suggested prompts, text input, send/clear/close controls.
- Submit with **Enter**, new line with **Shift+Enter**, close with **Escape**.
- Shows real API connection/error states and a typing animation while waiting.
- Messages display via `textContent`; returned text is not interpreted as HTML.
- Within the same browser tab, the latest conversation messages are saved in `sessionStorage` and restored when changing pages. The trash icon clears them. A new browser tab starts fresh.
- Closing/opening the fullscreen navigation does not leave the chat overlay blocking controls.
- Mobile layout and `prefers-reduced-motion` are supported.

## Static preview

```bash
cd frontend
python -m http.server 8765
```

Open `http://127.0.0.1:8765/` and `http://127.0.0.1:8765/dashboard.html?preview=1`. The launcher and panel are testable without a backend, but sending a prompt will clearly say the chatbot is not connected. To test real replies, configure your endpoint and start your backend server (and ensure CORS/same-origin routing is correct).

## Files added

- `dist/css/agrishift-chat.css`
- `dist/js/agrishift-chat-config.js`
- `dist/js/agrishift-chat.js`

Both HTML pages load these files using local paths. None of the original dashboards, crop data or analysis JS was replaced.
