import { ImageResponse } from "next/og";

export const runtime = "edge";

export const size = {
  width: 180,
  height: 180,
};
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: "36px",
          background: "linear-gradient(135deg, #1e1b4b 0%, #14141F 100%)",
          border: "4px solid #7c3aed",
        }}
      >
        <div
          style={{
            width: "90px",
            height: "90px",
            transform: "rotate(45deg)",
            border: "8px solid #a855f7",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "50%",
              background: "linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)",
            }}
          />
        </div>
      </div>
    ),
    {
      ...size,
    }
  );
}
