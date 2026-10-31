export function CelebrationArt() {
  return (
    <div className="celebration-art" aria-hidden="true">
      <svg viewBox="0 0 440 380" fill="none">
        <defs>
          <pattern
            id="stripes"
            width="16"
            height="16"
            patternUnits="userSpaceOnUse"
          >
            <path d="M0 0v16" stroke="#c9d8c6" strokeWidth="7" />
          </pattern>
        </defs>
        <path d="M90 284V128a130 130 0 0 1 260 0v156" fill="#e4eadc" />
        <path d="M104 284V128a116 116 0 0 1 232 0v156" fill="url(#stripes)" />
        <ellipse
          cx="222"
          cy="316"
          rx="158"
          ry="23"
          fill="#273b2a"
          opacity=".08"
        />
        <path
          d="M108 241h224l-15 78H125l-17-78Z"
          fill="#f9f5e9"
          stroke="#d8d1ba"
        />
        <path
          d="M115 240c0-10 47-17 105-17s105 7 105 17-47 17-105 17-105-7-105-17Z"
          fill="#fffdf5"
          stroke="#d8d1ba"
        />
        <path
          d="M117 250v53M142 256l-2 59M299 256l4 59M324 249v55"
          stroke="#e7dfc9"
          strokeWidth="2"
        />
        <ellipse cx="224" cy="242" rx="48" ry="10" fill="#d0d6b7" />
        <path d="M189 238v-39h70v39c0 13-70 13-70 0Z" fill="#d58266" />
        <ellipse cx="224" cy="199" rx="35" ry="9" fill="#f2bc9d" />
        <path
          d="M194 204c7 9 13-3 20 3s11 2 17-1 16 6 23-2"
          stroke="#f9e2bd"
          strokeWidth="5"
        />
        <path
          d="M211 193v-20M225 191v-23M239 193v-20"
          stroke="#f9f2d6"
          strokeWidth="4"
        />
        <path
          d="M211 170c-5-5 0-11 0-11s5 6 0 11ZM225 165c-5-5 0-11 0-11s5 6 0 11ZM239 170c-5-5 0-11 0-11s5 6 0 11Z"
          fill="#d39131"
        />
        <path
          d="M151 231v-38m-11-17c0 22 23 22 23 0l-2-18h-19l-2 18ZM139 233h24"
          stroke="#7f9474"
          strokeWidth="2"
        />
        <path
          d="M288 231v-38m-11-17c0 22 23 22 23 0l-2-18h-19l-2 18ZM276 233h24"
          stroke="#7f9474"
          strokeWidth="2"
        />
        <path d="M145 179h14M282 179h14" stroke="#d4a257" strokeWidth="5" />
        <path d="M75 101c16-24 30-18 27 0S80 123 75 101Z" fill="#dd977a" />
        <path
          d="M90 120c-3 28 26 30 15 56"
          stroke="#bb987a"
          strokeWidth="1.5"
        />
        <path d="M342 90c-16-35-47-22-43 2s30 30 43-2Z" fill="#d9bc66" />
        <path
          d="M316 114c-14 23 7 42-8 54"
          stroke="#bb987a"
          strokeWidth="1.5"
        />
        <path
          d="m189 47 4 11 11 4-11 4-4 11-4-11-11-4 11-4 4-11Z"
          fill="#658067"
        />
        <path d="m362 185 3 8 8 3-8 3-3 8-3-8-8-3 8-3 3-8Z" fill="#d7a749" />
        <path d="m64 228 3 8 8 3-8 3-3 8-3-8-8-3 8-3 3-8Z" fill="#658067" />
        <path
          d="m130 55 5-9M273 43l6 6M363 131l8-3M63 173l6 4"
          stroke="#c98a6d"
          strokeWidth="3"
          strokeLinecap="round"
        />
        <circle cx="251" cy="93" r="4" fill="#d4a257" />
        <circle cx="126" cy="132" r="3" fill="#658067" />
      </svg>
      <div className="art-note">
        <span className="mini-star">✦</span> Made for meaningful moments
      </div>
    </div>
  );
}
