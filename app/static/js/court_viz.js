// 2D top-down court visualization on canvas
class CourtViz {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.shots = [];
    this.activeFilter = 'all';
    this.onClickShot = null;

    // Court dimensions in feet
    this.COURT_L = 78;
    this.COURT_W = 27;
    this.NET_Y = 39;
    this.SVC_L = 21;

    this._resize();
  }

  _resize() {
    const W = this.canvas.width;
    const H = this.canvas.height;
    const PAD = 24;
    this.scaleX = (W - PAD * 2) / this.COURT_W;
    this.scaleY = (H - PAD * 2) / this.COURT_L;
    this.offX = PAD;
    this.offY = PAD;
  }

  _courtPx(cx, cy) {
    return [
      this.offX + (cx + this.COURT_W / 2) * this.scaleX,
      this.offY + cy * this.scaleY,
    ];
  }

  drawCourt() {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    // Background
    ctx.fillStyle = '#1a1d26';
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    ctx.strokeStyle = '#4a5568';
    ctx.lineWidth = 1.5;

    const lines = [
      // Baselines
      [[-13.5, 0], [13.5, 0]],
      [[-13.5, 78], [13.5, 78]],
      // Sidelines
      [[-13.5, 0], [-13.5, 78]],
      [[13.5, 0], [13.5, 78]],
      // Net
      [[-13.5, 39], [13.5, 39]],
      // Service lines
      [[-13.5, 57], [13.5, 57]],
      [[-13.5, 21], [13.5, 21]],
      // Center service line
      [[0, 21], [0, 57]],
    ];

    for (const [[x1, y1], [x2, y2]] of lines) {
      const [px1, py1] = this._courtPx(x1, y1);
      const [px2, py2] = this._courtPx(x2, y2);
      ctx.beginPath();
      ctx.moveTo(px1, py1);
      ctx.lineTo(px2, py2);
      ctx.stroke();
    }

    // Net label
    const [nx, ny] = this._courtPx(0, 39);
    ctx.fillStyle = '#4a5568';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('NET', nx, ny - 6);
  }

  setShots(shots) {
    this.shots = shots;
    this.render();
  }

  filterType(type) {
    this.activeFilter = type;
    this.render();
  }

  render() {
    this.drawCourt();
    const ctx = this.ctx;
    const filtered = this.activeFilter === 'all'
      ? this.shots
      : this.shots.filter(s => s.shot_type === this.activeFilter);

    this._dotAreas = [];

    for (const shot of filtered) {
      if (shot.bounce_court_x == null || shot.bounce_court_y == null) continue;
      const [px, py] = this._courtPx(shot.bounce_court_x, shot.bounce_court_y);
      const r = 5 + (shot.quality_score || 0) / 25;

      let color;
      if (shot.is_close_call) color = '#f59e0b';
      else if (shot.is_in) color = '#4ade80';
      else color = '#f87171';

      ctx.beginPath();
      ctx.arc(px, py, r, 0, Math.PI * 2);
      ctx.fillStyle = color + 'cc';
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.stroke();

      this._dotAreas.push({ shot, px, py, r });
    }

    this._bindHover();
  }

  _bindHover() {
    this.canvas.onmousemove = (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const mx = (e.clientX - rect.left) * (this.canvas.width / rect.width);
      const my = (e.clientY - rect.top) * (this.canvas.height / rect.height);

      for (const dot of this._dotAreas) {
        const dist = Math.hypot(mx - dot.px, my - dot.py);
        if (dist <= dot.r + 3) {
          this.canvas.title = `#${dot.shot.shot_number} | ${dot.shot.shot_type} | ${dot.shot.spin_type} | ${dot.shot.speed_mph ? dot.shot.speed_mph.toFixed(0) + ' mph' : '--'} | Q:${dot.shot.quality_score || '--'}`;
          return;
        }
      }
      this.canvas.title = '';
    };

    this.canvas.onclick = (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const mx = (e.clientX - rect.left) * (this.canvas.width / rect.width);
      const my = (e.clientY - rect.top) * (this.canvas.height / rect.height);
      for (const dot of this._dotAreas) {
        if (Math.hypot(mx - dot.px, my - dot.py) <= dot.r + 3) {
          if (this.onClickShot) this.onClickShot(dot.shot);
          return;
        }
      }
    };
  }
}

const courtViz = new CourtViz('court-canvas');
