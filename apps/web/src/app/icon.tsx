import { ImageResponse } from "next/og";

export const runtime = "edge";

export const size = {
  width: 32,
  height: 32,
};
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: "8px",
          background: "linear-gradient(135deg, #1e1b4b 0%, #14141F 100%)",
          border: "1.5px solid #7c3aed",
          position: "relative",
        }}
      >
        <div
          style={{
            width: "16px",
            height: "16px",
            transform: "rotate(45deg)",
            border: "2px solid #a855f7",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "50%",
              background: "#6366f1",
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
