/** 다계열을 색만으로 구분하지 않도록 선 모양을 달리한다. */
export const LINE_DASHES = [undefined, "6 3", "2 3", "8 3 2 3", "1 4", "10 4", "4 2 1 2", "3 3"];

/** 이 개수 이하(한 달 일자별까지)면 각 값을 읽을 수 있게 선 위에 점을 찍는다. 많으면 점이 선을 가린다. */
export const LINE_DOT_MAX_POINTS = 31;

export function lineDot(pointCount: number) {
  // 점선 계열이어도 점 테두리는 실선으로 그린다.
  return pointCount <= LINE_DOT_MAX_POINTS
    ? { r: 3, strokeWidth: 2, strokeDasharray: "0", fill: "var(--canvas)" }
    : false;
}
