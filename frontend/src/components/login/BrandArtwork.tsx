import { useId } from "react";
import "./brand-artwork.css";

const words = [
  { text: "SEEK", x: 32, y: 214, size: 180, width: 330 },
  { text: "THE", x: 374, y: 242, size: 70, width: 80 },
  { text: "WAY", x: 64, y: 528, size: 326, width: 520 },
  { text: "YOU", x: 112, y: 598, size: 74, width: 86 },
  { text: "WANT.", x: 292, y: 704, size: 170, width: 318 },
  { text: "LIVE THE", x: 104, y: 810, size: 46, width: 168 },
  { text: "LIFE", x: 290, y: 870, size: 136, width: 210 },
  { text: "YOU FOUND.", x: 338, y: 930, size: 46, width: 242 },
];

/** 桌面字场与窄屏文案共用同一内容，避免品牌文字分叉。 */
export function BrandArtwork() {
  const id = useId();
  return (
    <>
      <svg
        className="brand-artwork"
        viewBox="0 0 700 960"
        role="img"
        aria-label={words.map(({ text }) => text).join(" ")}
      >
        <defs>
          <clipPath id={`${id}-body`}>
            <path d="M0 0H700V384H0ZM0 393H700V960H0Z" />
          </clipPath>
          <clipPath id={`${id}-slice`}>
            <path d="M0 384H700V393H0Z" />
          </clipPath>
          <clipPath id={`${id}-trail`}>
            <path d="M450 280H700V292H450ZM450 345H700V352H450ZM450 448H700V461H450Z" />
          </clipPath>
        </defs>
        <g aria-hidden="true" clipPath={`url(#${id}-body)`}>
          {words.map(({ text, x, y, size, width }) => (
            <text
              key={text}
              id={text === "WAY" ? `${id}-way` : undefined}
              x={x}
              y={y}
              fontSize={size}
              textLength={width}
              lengthAdjust="spacingAndGlyphs"
              transform={`translate(${y * 0.17} 0) skewX(-9.65)`}
            >
              {text === "WAY" ? (
                <>
                  <tspan>W</tspan>
                  <tspan className="brand-artwork__outline">A</tspan>
                  <tspan>Y</tspan>
                </>
              ) : (
                text
              )}
            </text>
          ))}
        </g>
        <g aria-hidden="true">
          <use
            href={`#${id}-way`}
            transform="translate(24 0)"
            clipPath={`url(#${id}-trail)`}
            className="brand-artwork__trail"
          />
          <use href={`#${id}-way`} transform="translate(-12 0)" clipPath={`url(#${id}-slice)`} />
        </g>
      </svg>
      <p className="brand-artwork__compact">
        <span>
          {words
            .slice(0, 5)
            .map(({ text }) => text)
            .join(" ")}
        </span>
        <span>
          {words
            .slice(5)
            .map(({ text }) => text)
            .join(" ")}
        </span>
      </p>
    </>
  );
}
