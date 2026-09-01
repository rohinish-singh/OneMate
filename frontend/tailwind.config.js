/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "#F8F9FA",
        surface: {
          DEFAULT: "#FFFFFF",
          secondary: "#F3F4F6",
          hover: "#F9FAFB",
        },
        border: {
          DEFAULT: "#E5E7EB",
          subtle: "#F0F1F3",
          strong: "#111827",
        },
        charcoal: {
          DEFAULT: "#111827",
          muted: "#4B5563",
          caption: "#6B7280",
          disabled: "#9CA3AF",
        },
        brand: {
          DEFAULT: "#1E293B",
          hover: "#0F172A",
          tint: "#F1F5F9",
        },
        semantic: {
          same: {
            bg: "#ECFDF5",
            border: "#A7F3D0",
            text: "#065F46",
          },
          potential: {
            bg: "#FFFBEB",
            border: "#FDE68A",
            text: "#92400E",
          },
          diff: {
            bg: "#FEF2F2",
            border: "#FECACA",
            text: "#991B1B",
          },
          neutral: {
            bg: "#F3F4F6",
            border: "#E5E7EB",
            text: "#374151",
          },
        },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        'page-title': ['20px', { lineHeight: '26px', letterSpacing: '-0.02em', fontWeight: '600' }],
        'section-title': ['16px', { lineHeight: '22px', letterSpacing: '-0.01em', fontWeight: '600' }],
        'card-title': ['14px', { lineHeight: '20px', fontWeight: '600' }],
        'table-header': ['11px', { lineHeight: '16px', letterSpacing: '0.05em', fontWeight: '500' }],
        'body': ['13px', { lineHeight: '18px' }],
        'body-sm': ['12px', { lineHeight: '16px' }],
      },
      borderRadius: {
        badge: "4px",
        input: "6px",
        panel: "8px",
      },
    },
  },
  plugins: [],
}
