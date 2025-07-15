import { useReportStore } from "@/stores/report";
import { useModeStore } from "@/stores/dependencyMode";

export default function TooltipCanvasDrawer(canvas) {
	const reportStore = useReportStore();
	const modeStore = useModeStore();

	if (!(canvas instanceof HTMLCanvasElement)) {
		throw new Error('Provided element is not a canvas.');
	}

	const ctx = canvas.getContext('2d');
	const shapes = [];

	canvas.height = reportStore.nodes.filter(item => item.type === 'paragraph').length * 110 + ((modeStore.mode === 'structure') * reportStore.nodes.filter(item => item.type === 'header').length * 90) + 10;

	const dpr = window.devicePixelRatio || 1;

	const canvasWidth = 130;
	const canvasHeight = canvas.height;
  
	canvas.width = canvasWidth * dpr;
	canvas.height = canvasHeight * dpr;
  
	canvas.style.width = `${canvasWidth}px`;
	canvas.style.height = `${canvasHeight}px`;
  
	ctx.scale(dpr, dpr);

	let tooltip;

	if (document.getElementById('node-link-tooltip')) {
		tooltip = document.getElementById('node-link-tooltip');
	} else {
		tooltip = document.createElement('div');
		tooltip.id = 'node-link-tooltip';
		tooltip.style.position = 'absolute';
		tooltip.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
		tooltip.style.color = 'white';
		tooltip.style.padding = '5px';
		tooltip.style.borderRadius = '3px';
		tooltip.style.pointerEvents = 'none';
		tooltip.style.display = 'none';
		document.body.appendChild(tooltip);
	}

	canvas.addEventListener('mousemove', (event) => {
		const rect = canvas.getBoundingClientRect();
		const mouseX = event.clientX - rect.left;
		const mouseY = event.clientY - rect.top;
		let found = false;

		for (const shape of shapes) {
			if (shape.type === 'circle' && isMouseInCircle(mouseX, mouseY, shape) && shape.tooltip) {
				showTooltip(event.clientX, event.clientY, shape.tooltip);
				found = true;
				break;
			} else if (shape.type === 'line' && isMouseOnLine(mouseX, mouseY, shape) && shape.tooltip) {
				showTooltip(event.clientX, event.clientY, shape.tooltip);
				found = true;
				break;
			} else if (shape.type === 'curve' && isMouseOnCurve(mouseX, mouseY, shape) && shape.tooltip) {
				showTooltip(event.clientX, event.clientY, shape.tooltip);
				found = true;
				break;
			}
		}

		if (!found) {
			tooltip.style.display = 'none';
		}
	});

	function showTooltip(x, y, text) {
		tooltip.innerText = text;
		tooltip.style.left = `${x + 10}px`;
		tooltip.style.top = `${y + 10}px`;
		tooltip.style.display = 'block';
	}

	function isMouseInCircle(mouseX, mouseY, circle) {
		const dx = mouseX - circle.x;
		const dy = mouseY - circle.y;
		return dx * dx + dy * dy <= circle.radius * circle.radius;
	}

	function isMouseOnLine(mouseX, mouseY, line) {
		const { startX, startY, endX, endY, lineWidth } = line;
		const distance =
			Math.abs((endY - startY) * mouseX - (endX - startX) * mouseY + endX * startY - endY * startX) /
			Math.sqrt((endY - startY) ** 2 + (endX - startX) ** 2);
		const dotProduct = (mouseX - startX) * (mouseX - endX) + (mouseY - startY) * (mouseY - endY);
		return distance <= lineWidth * 2 && dotProduct < 0;
	}

	function isMouseOnCurve(mouseX, mouseY, curve) {
		const { startX, startY, cp1X, cp1Y, cp2X, cp2Y, endX, endY, lineWidth } = curve;
		const numSteps = 1;
		for (let i = 0; i < numSteps; i++) {
			const t = i / numSteps;
			const nt = (i + 1) / numSteps;
			const x = (1 - t) ** 3 * startX +
					3 * (1 - t) ** 2 * t * cp1X +
					3 * (1 - t) * (t ** 2) * cp2X +
					t ** 3 * endX;
			const y = (1 - t) ** 3 * startY +
					3 * (1 - t) ** 2 * t * cp1Y +
					3 * (1 - t) * (t ** 2) * cp2Y +
					t ** 3 * endY;
			const nx = (1 - nt) ** 3 * startX +
					3 * (1 - nt) ** 2 * nt * cp1X +
					3 * (1 - nt) * (nt ** 2) * cp2X +
					nt ** 3 * endX;
			const ny = (1 - nt) ** 3 * startY +
					3 * (1 - nt) ** 2 * nt * cp1Y +
					3 * (1 - nt) * (nt ** 2) * cp2Y +
					nt ** 3 * endY;
			if (isMouseOnLine(mouseX, mouseY, { type: 'line', startX: x, startY: y, endX: nx, endY: ny, lineWidth, tooltip: '' }))
				return true;
		}
		return false;
	}

	return {
		drawCircle: function ({ x, y, radius = 10, lineWidth = 1, strokeColor = 'black', fillColor = 'white', text = '', textColor = 'white', tooltipText = '' }) {
			ctx.beginPath();
			ctx.arc(x, y, radius, 0, Math.PI * 2);
			ctx.lineWidth = lineWidth;
			ctx.strokeStyle = strokeColor;
			ctx.fillStyle = fillColor;
			ctx.fill();
			ctx.stroke();

			if (text) {
				ctx.fillStyle = textColor;
				ctx.font = `${radius * 1.35}px Arial`;
				ctx.textAlign = 'center';
				ctx.textBaseline = 'middle';
				ctx.fillText(text, x, y);
			}

			shapes.push({ type: 'circle', x, y, radius, tooltip: tooltipText });
		},

		drawCurve: function({ startX, startY, cp1X, cp1Y, cp2X, cp2Y, endX, endY, lineWidth = 1, strokeColor = 'black', tooltipText = '' }) {
			ctx.beginPath();
			ctx.moveTo(startX, startY);
			ctx.bezierCurveTo(cp1X, cp1Y, cp2X, cp2Y, endX, endY);
			ctx.lineWidth = lineWidth;
			ctx.strokeStyle = strokeColor;
			ctx.stroke();

			shapes.push({ type: 'curve', startX, startY, cp1X, cp1Y, cp2X, cp2Y, endX, endY, lineWidth, tooltip: tooltipText });
		},

		drawLine: function ({ startX, startY, endX, endY, lineWidth = 1, strokeColor = 'black', tooltipText = '' }) {
			ctx.beginPath();
			ctx.moveTo(startX, startY);
			ctx.lineTo(endX, endY);
			ctx.lineWidth = lineWidth;
			ctx.strokeStyle = strokeColor;
			ctx.stroke();

			shapes.push({ type: 'line', startX, startY, endX, endY, lineWidth, tooltip: tooltipText });
		}
	};
}
