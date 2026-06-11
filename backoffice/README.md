# SpiderShare Backoffice

React + Vite + TypeScript backoffice for operating SpiderShare.

## Local dev

```bash
npm install
npm run dev
```

Default URL: `http://localhost:5173`.

The app uses mock data by default until the `/admin/...` API exists.

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_USE_MOCKS=true
```

Set `VITE_USE_MOCKS=false` when the admin endpoints are implemented.
