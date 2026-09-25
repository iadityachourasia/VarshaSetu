/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          950: '#090d16',
          900: '#0f172a',
          850: '#131e36',
          800: '#172554',
          700: '#1e3a8a',
          600: '#2563eb',
        },
        indigo: {
          950: '#0c0a24',
          900: '#1e1b4b',
          800: '#312e81',
          700: '#3730a3',
          600: '#4f46e5',
        },
        violet: {
          900: '#3b0764',
          800: '#581c87',
          700: '#6b21a8',
          600: '#7c3aed',
        },
        slate: {
          900: '#0f172a',
          800: '#1e293b',
          700: '#334155',
          600: '#475569',
          500: '#64748b',
          400: '#94a3b8',
          300: '#cbd5e1',
          100: '#f1f5f9',
          50:  '#f8fafc',
        }
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(15, 23, 42, 0.08)',
        'glass-hover': '0 12px 40px 0 rgba(37, 99, 235, 0.15)',
        'neon-blue': '0 0 20px 0 rgba(37, 99, 235, 0.25)',
        'neon-emerald': '0 0 20px 0 rgba(16, 185, 129, 0.25)',
        'neon-violet': '0 0 20px 0 rgba(124, 58, 237, 0.25)',
      }
    },
  },
  plugins: [],
}
