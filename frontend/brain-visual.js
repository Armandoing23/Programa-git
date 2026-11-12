(function () {
    class ParticleSphere {
        constructor({ canvasId, particleCount = 4200 } = {}) {
            this.canvas = document.getElementById(canvasId);
            this.particleCount = particleCount;
            this.animationId = null;
            this.particles = [];

            if (!this.canvas) {
                return;
            }

            this.ctx = this.canvas.getContext('2d');
            this.init();
        }

        init() {
            this.resize();
            this.buildParticles();
            this.start();
            window.addEventListener('resize', () => this.resize());
        }

        resize() {
            if (!this.canvas || !this.ctx) return;

            const ratio = window.devicePixelRatio || 1;
            const size = Math.min(window.innerWidth * 0.75, 820);

            this.canvas.width = size * ratio;
            this.canvas.height = size * ratio;
            this.canvas.style.width = `${size}px`;
            this.canvas.style.height = `${size}px`;
            this.ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
        }

        buildParticles() {
            this.particles = [];
            const radius = 240;

            for (let i = 0; i < this.particleCount; i++) {
                const theta = Math.random() * Math.PI * 2;
                const phi = Math.acos(2 * Math.random() - 1);
                const spread = radius * (0.78 + Math.random() * 0.42);
                const x = spread * Math.sin(phi) * Math.cos(theta);
                const y = spread * Math.cos(phi);
                const z = spread * Math.sin(phi) * Math.sin(theta);

                this.particles.push({
                    x,
                    y,
                    z,
                    vx: (Math.random() - 0.5) * 0.22,
                    vy: (Math.random() - 0.5) * 0.22,
                    vz: (Math.random() - 0.5) * 0.22,
                    r: Math.random() * 1.7 + 0.8,
                    hue: 205 + Math.random() * 90,
                    alpha: 0.45 + Math.random() * 0.55
                });
            }
        }

        draw() {
            if (!this.canvas || !this.ctx) return;

            const width = this.canvas.clientWidth;
            const height = this.canvas.clientHeight;
            const cx = width / 2;
            const cy = height / 2;

            this.ctx.clearRect(0, 0, width, height);

            const rotY = performance.now() * 0.00072;
            const rotX = Math.PI / 3.1;
            const projected = [];

            this.ctx.beginPath();
            this.ctx.fillStyle = 'rgba(90, 130, 255, 0.08)';
            this.ctx.arc(cx, cy, 230, 0, Math.PI * 2);
            this.ctx.fill();

            for (const p of this.particles) {
                const x1 = p.x;
                const y1 = p.y * Math.cos(rotX) - p.z * Math.sin(rotX);
                const z1 = p.y * Math.sin(rotX) + p.z * Math.cos(rotX);

                const x2 = x1 * Math.cos(rotY) + z1 * Math.sin(rotY);
                const z2 = -x1 * Math.sin(rotY) + z1 * Math.cos(rotY);

                const perspective = 700 / (700 + z2);
                const sx = cx + x2 * perspective;
                const sy = cy + y1 * perspective;

                const distToCenter = Math.sqrt(x2 * x2 + y1 * y1 + z2 * z2);
                const brightness = Math.min(1, Math.max(0.15, (distToCenter / 260) * 1.15));

                p.screenX = sx;
                p.screenY = sy;
                p.depth = z2;
                p.brightness = brightness;
                projected.push(p);
            }

            projected.sort((a, b) => a.depth - b.depth);

            this.ctx.globalCompositeOperation = 'screen';
            for (const p of projected) {
                const opacity = Math.min(1, Math.max(0.25, p.alpha * (0.65 + p.brightness)));
                const hue = p.hue + (p.depth + 260) * 0.07;

                this.ctx.beginPath();
                this.ctx.fillStyle = `hsla(${hue}, 100%, 72%, ${opacity})`;
                this.ctx.shadowColor = `hsla(${hue}, 100%, 70%, 0.9)`;
                this.ctx.shadowBlur = 10 + p.brightness * 18;
                this.ctx.arc(p.screenX, p.screenY, p.r + p.brightness * 0.85, 0, Math.PI * 2);
                this.ctx.fill();
            }
            this.ctx.globalCompositeOperation = 'source-over';
            this.ctx.shadowBlur = 0;
        }

        animate() {
            if (!this.canvas || !this.ctx || this.particles.length === 0) return;

            const t = performance.now() * 0.001;

            for (const p of this.particles) {
                p.x += p.vx + Math.sin(t * 1.4 + p.y * 0.04) * 0.22;
                p.y += p.vy + Math.cos(t * 1.3 + p.z * 0.035) * 0.22;
                p.z += p.vz + Math.sin(t * 1.2 + p.x * 0.03) * 0.22;

                const dist = Math.sqrt(p.x * p.x + p.y * p.y + p.z * p.z);
                const target = 240 + Math.sin(t + p.x * 0.04) * 16;

                if (dist > target || dist < target * 0.72) {
                    const scalar = target / Math.max(dist, 0.0001);
                    p.x *= scalar * 0.98;
                    p.y *= scalar * 0.98;
                    p.z *= scalar * 0.98;
                }
            }

            this.draw();
            this.animationId = requestAnimationFrame(() => this.animate());
        }

        start() {
            if (!this.canvas || !this.ctx) return;
            cancelAnimationFrame(this.animationId);
            this.animationId = requestAnimationFrame(() => this.animate());
        }

        destroy() {
            if (this.animationId) {
                cancelAnimationFrame(this.animationId);
            }
        }
    }

    window.ParticleSphere = ParticleSphere;
})();
