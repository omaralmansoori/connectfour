// Tree visualization for Connect Four / Tic-Tac-Toe AI diagnostics - Educational Version
class TreeVisualizer {
  constructor(treeData, principalVariation, evaluatedMoves, gameType = 'connectfour') {
    this.treeData = treeData;
    this.principalVariation = principalVariation || [];
    this.evaluatedMoves = evaluatedMoves || [];
    this.container = document.getElementById('treeContainer');
    this.gameType = gameType; // 'connectfour' or 'tictactoe'
    this.showScores = true;
    this.highlightBest = true;
    this.showBestOnly = true;
    this.maxDepthToShow = 4;
    
    // Track collapsed nodes by their unique path
    this.collapsedNodes = new Set();
    
    this.nodeWidth = 180;
    this.nodeHeight = 85;
    this.levelHeight = 140;
    this.horizontalSpacing = 40;
    
    this.setupControls();
    this.render();
  }
  
  // Format move label based on game type
  formatMove(move) {
    if (this.gameType === 'tictactoe') {
      const row = Math.floor(move / 3) + 1;
      const col = (move % 3) + 1;
      return `Cell (${row},${col})`;
    }
    return `Column ${move}`;
  }
  
  setupControls() {
    const showScoresCheckbox = document.getElementById('showScores');
    const highlightBestCheckbox = document.getElementById('highlightBest');
    const showBestOnlyCheckbox = document.getElementById('showBestOnly');
    
    if (showScoresCheckbox) {
      showScoresCheckbox.addEventListener('change', (e) => {
        this.showScores = e.target.checked;
        this.render();
      });
    }
    
    if (highlightBestCheckbox) {
      highlightBestCheckbox.addEventListener('change', (e) => {
        this.highlightBest = e.target.checked;
        this.render();
      });
    }
    
    if (showBestOnlyCheckbox) {
      showBestOnlyCheckbox.addEventListener('change', (e) => {
        this.showBestOnly = e.target.checked;
        this.render();
      });
    }
  }
  
  // Generate a unique path identifier for a node
  getNodePath(node, level, parentPath = '') {
    const col = node.column !== null && node.column !== undefined ? node.column : 'root';
    return parentPath ? `${parentPath}-${col}` : `${col}`;
  }
  
  // Toggle collapse state for a node
  toggleCollapse(nodePath) {
    if (this.collapsedNodes.has(nodePath)) {
      this.collapsedNodes.delete(nodePath);
    } else {
      this.collapsedNodes.add(nodePath);
    }
    this.render();
  }
  
  collectNodesForDisplay() {
    const nodes = [];
    
    const traverse = (node, level = 0, parentIndex = -1, isInBestPath = true, parentPath = '') => {
      if (!node || level > this.maxDepthToShow) return;
      
      // Generate unique path for this node
      const nodePath = this.getNodePath(node, level, parentPath);
      
      // Determine if this node is in the principal variation
      const nodeInPV = level === 0 || (
        level > 0 && 
        this.principalVariation.length >= level && 
        node.column === this.principalVariation[level - 1]
      );
      
      const inBest = isInBestPath && nodeInPV;
      
      // Skip if showBestOnly and not in best path
      if (this.showBestOnly && level > 0 && !inBest) {
        return;
      }
      
      const hasChildren = node.children && node.children.length > 0;
      const isCollapsed = this.collapsedNodes.has(nodePath);
      
      const nodeInfo = {
        node: node,
        level: level,
        parentIndex: parentIndex,
        isInBestPath: inBest,
        index: nodes.length,
        nodePath: nodePath,
        hasChildren: hasChildren,
        isCollapsed: isCollapsed
      };
      
      nodes.push(nodeInfo);
      const currentIndex = nodes.length - 1;
      
      // Process children only if not collapsed
      if (hasChildren && !isCollapsed) {
        node.children.forEach(child => {
          traverse(child, level + 1, currentIndex, inBest, nodePath);
        });
      }
    };
    
    traverse(this.treeData);
    return nodes;
  }
  
  render() {
    this.container.innerHTML = '';
    
    if (!this.treeData) {
      this.container.innerHTML = '<p style="color: var(--muted); padding: 20px;">No tree data available. Make a move to see the AI\'s decision process.</p>';
      return;
    }
    
    const nodes = this.collectNodesForDisplay();
    
    if (nodes.length === 0) {
      this.container.innerHTML = '<p style="color: var(--muted); padding: 20px;">No nodes to display</p>';
      return;
    }
    
    // Calculate positions for each level
    const levelNodes = {};
    nodes.forEach(n => {
      if (!levelNodes[n.level]) levelNodes[n.level] = [];
      levelNodes[n.level].push(n);
    });
    
    // Assign x positions
    nodes.forEach((n, idx) => {
      const levelIndex = levelNodes[n.level].indexOf(n);
      n.x = levelIndex * (this.nodeWidth + this.horizontalSpacing);
      n.y = n.level * this.levelHeight + 120; // Add offset to prevent overlap with summary
    });
    
    // Calculate bounds
    const maxX = Math.max(...nodes.map(n => n.x)) + this.nodeWidth;
    const maxY = Math.max(...nodes.map(n => n.y)) + this.nodeHeight + 40; // Extra bottom padding
    
    // Create container
    const width = Math.max(maxX + 60, 800);
    const height = maxY + 100;
    
    this.container.style.position = 'relative';
    this.container.style.width = width + 'px';
    this.container.style.minHeight = height + 'px';
    
    // Create SVG for edges
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.style.position = 'absolute';
    svg.style.top = '0';
    svg.style.left = '0';
    svg.style.width = width + 'px';
    svg.style.height = height + 'px';
    svg.style.pointerEvents = 'none';
    this.container.appendChild(svg);
    
    // Draw edges
    nodes.forEach(n => {
      if (n.parentIndex >= 0) {
        const parent = nodes[n.parentIndex];
        const isInBest = this.highlightBest && n.isInBestPath && parent.isInBestPath;
        this.drawEdge(
          svg,
          parent.x + this.nodeWidth / 2 + 30,
          parent.y + this.nodeHeight + 30,
          n.x + this.nodeWidth / 2 + 30,
          n.y + 30,
          isInBest
        );
      }
    });
    
    // Draw nodes
    nodes.forEach(n => {
      this.drawNode(n);
    });
    
    // Add summary
    this.addSummary();
  }
  
  addSummary() {
    const summary = document.createElement('div');
    summary.style.cssText = `
      background: rgba(12, 18, 33, 0.98);
      padding: 16px;
      border-radius: 10px;
      margin-bottom: 32px;
      border: 2px solid var(--accent);
      box-shadow: 0 4px 12px rgba(93, 208, 255, 0.2);
      position: relative;
      z-index: 10;
    `;
    
    const bestMove = this.principalVariation.length > 0 ? this.principalVariation[0] : null;
    const bestEval = this.evaluatedMoves.find(m => m.column === bestMove);
    const bestScore = bestEval ? bestEval.score : 'N/A';
    const bestMoveLabel = bestMove !== null ? this.formatMove(bestMove) : 'N/A';
    
    summary.innerHTML = `
      <div style="display: flex; gap: 24px; align-items: center; flex-wrap: wrap; justify-content: center;">
        <div style="text-align: center;">
          <div style="color: var(--muted); font-size: 12px; margin-bottom: 4px;">AI's Chosen Move</div>
          <div style="color: var(--ai); font-size: 24px; font-weight: 700;">${bestMoveLabel}</div>
        </div>
        <div style="text-align: center;">
          <div style="color: var(--muted); font-size: 12px; margin-bottom: 4px;">Evaluated Score</div>
          <div style="color: var(--accent); font-size: 24px; font-weight: 700;">${bestScore}</div>
        </div>
        <div style="text-align: center; padding: 8px 16px; background: rgba(93, 208, 255, 0.1); border-radius: 8px;">
          <div style="color: var(--text); font-size: 13px;">
            ${this.showBestOnly ? '📍 Showing Principal Variation (Best Path)' : '🌳 Showing Full Search Tree'}
          </div>
        </div>
      </div>
    `;
    
    this.container.insertBefore(summary, this.container.firstChild);
  }
  
  drawEdge(svg, x1, y1, x2, y2, isInBest) {
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', x1);
    line.setAttribute('y1', y1);
    line.setAttribute('x2', x2);
    line.setAttribute('y2', y2);
    
    if (isInBest) {
      line.style.stroke = 'var(--accent)';
      line.style.strokeWidth = '4';
      line.style.strokeDasharray = 'none';
      line.style.filter = 'drop-shadow(0 0 6px rgba(93, 208, 255, 0.8))';
    } else {
      line.style.stroke = 'rgba(159, 177, 208, 0.25)';
      line.style.strokeWidth = '2';
    }
    
    svg.appendChild(line);
  }
  
  drawNode(nodeInfo) {
    const node = nodeInfo.node;
    const nodeEl = document.createElement('div');
    nodeEl.className = 'tree-node';
    
    const isAITurn = node.maximizing;
    nodeEl.classList.add(isAITurn ? 'ai-turn' : 'human-turn');
    
    if (this.highlightBest && nodeInfo.isInBestPath) {
      nodeEl.classList.add('best-path');
    }
    
    // Add collapsible class if node has children
    if (nodeInfo.hasChildren) {
      nodeEl.classList.add('collapsible');
      if (nodeInfo.isCollapsed) {
        nodeEl.classList.add('collapsed');
      }
    }
    
    nodeEl.style.left = (nodeInfo.x + 30) + 'px';
    nodeEl.style.top = (nodeInfo.y + 30) + 'px';
    
    const moveDesc = nodeInfo.level === 0 
      ? '🎯 Current State' 
      : `${isAITurn ? '🤖' : '👤'} ${this.formatMove(node.column)}`;
    
    const scoreDisplay = this.showScores 
      ? `<div class="node-score">Score: ${node.score}</div>`
      : '';
    
    // Add collapse indicator for nodes with children
    const collapseIndicator = nodeInfo.hasChildren 
      ? `<span class="collapse-indicator">${nodeInfo.isCollapsed ? '▶' : '▼'}</span>` 
      : '';
    
    const childCount = nodeInfo.hasChildren && nodeInfo.isCollapsed
      ? `<div class="collapsed-hint">${node.children.length} hidden</div>`
      : '';
    
    nodeEl.innerHTML = `
      <div class="node-label">${collapseIndicator}${moveDesc}</div>
      <div class="node-info">
        <div style="font-size: 11px;">Level ${nodeInfo.level} • ${isAITurn ? 'AI Maximizes' : 'Human Minimizes'}</div>
        ${scoreDisplay}
        ${childCount}
      </div>
    `;
    
    // Add click handler to toggle collapse
    if (nodeInfo.hasChildren) {
      nodeEl.addEventListener('click', (e) => {
        e.stopPropagation();
        this.toggleCollapse(nodeInfo.nodePath);
      });
    }
    
    nodeEl.addEventListener('mouseenter', (e) => {
      this.showTooltip(e, nodeInfo);
    });
    
    nodeEl.addEventListener('mouseleave', () => {
      this.hideTooltip();
    });
    
    this.container.appendChild(nodeEl);
  }
  
  showTooltip(event, nodeInfo) {
    const node = nodeInfo.node;
    let tooltip = document.querySelector('.node-tooltip');
    if (!tooltip) {
      tooltip = document.createElement('div');
      tooltip.className = 'node-tooltip';
      document.body.appendChild(tooltip);
r    }
    
    const moveInfo = node.column !== null && node.column !== undefined 
      ? this.formatMove(node.column) 
      : 'Root (Current Board State)';
    
    const pvInfo = nodeInfo.isInBestPath 
      ? '<div style="color: var(--accent); font-weight: 700; margin-bottom: 6px;">⭐ Part of Best Path</div>'
      : '';
    
    const explanation = node.maximizing 
      ? 'AI evaluates moves to find the highest score'
      : 'AI predicts human will choose the lowest score';
    
    const hasChildren = node.children && node.children.length > 0;
    const collapseHint = hasChildren 
      ? `<div style="margin-top: 6px; color: var(--accent); font-size: 11px;">💡 Click to ${nodeInfo.isCollapsed ? 'expand' : 'collapse'} children</div>`
      : '';
    
    tooltip.innerHTML = `
      <div style="margin-bottom: 8px; font-size: 14px;"><strong>Node Information</strong></div>
      ${pvInfo}
      <div style="margin: 4px 0;"><strong>Move:</strong> ${moveInfo}</div>
      <div style="margin: 4px 0;"><strong>Tree Level:</strong> ${nodeInfo.level}</div>
      <div style="margin: 4px 0;"><strong>Score:</strong> ${node.score}</div>
      <div style="margin: 4px 0;"><strong>Player:</strong> ${node.maximizing ? 'AI' : 'Human'}</div>
      <div style="margin: 4px 0;"><strong>Child Nodes:</strong> ${node.children ? node.children.length : 0}</div>
      <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--panel-border); color: var(--muted); font-size: 11px;">
        ${explanation}
      </div>
      ${collapseHint}
    `;
    
    tooltip.classList.add('visible');
    
    const rect = event.target.getBoundingClientRect();
    const tooltipX = Math.min(rect.right + 10, window.innerWidth - 320);
    tooltip.style.left = tooltipX + 'px';
    tooltip.style.top = rect.top + window.scrollY + 'px';
  }
  
  hideTooltip() {
    const tooltip = document.querySelector('.node-tooltip');
    if (tooltip) {
      tooltip.classList.remove('visible');
    }
  }
}

// Initialize tree visualization
document.addEventListener('DOMContentLoaded', () => {
  if (typeof treeData !== 'undefined' && typeof principalVariation !== 'undefined') {
    const evaluatedMoves = typeof evaluatedMovesData !== 'undefined' ? evaluatedMovesData : [];
    const gameType = typeof gameTypeData !== 'undefined' ? gameTypeData : 'connectfour';
    new TreeVisualizer(treeData, principalVariation, evaluatedMoves, gameType);
  }
});
