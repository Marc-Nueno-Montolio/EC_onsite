document.addEventListener('DOMContentLoaded', function() {
    // Initialize mermaid with custom config
    mermaid.initialize({
        startOnLoad: true,
        theme: 'neutral',
        securityLevel: 'loose',
        flowchart: {
            curve: 'basis',
            padding: 20
        },
        themeVariables: {
            fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
            fontSize: '16px',
            primaryColor: '#3b82f6',
            primaryTextColor: '#fff',
            lineColor: '#64748b',
            secondaryColor: '#10b981',
            tertiaryColor: '#6366f1'
        }
    });

    // Add controls functionality
    document.querySelectorAll('.mermaid-wrapper').forEach(wrapper => {
        const mermaidDiv = wrapper.querySelector('.mermaid');
        let scale = 1;
        let panning = false;
        let start = { x: 0, y: 0 };
        let translate = { x: 0, y: 0 };

        // Zoom controls
        wrapper.querySelector('.zoom-in').addEventListener('click', () => {
            scale = Math.min(scale * 1.2, 3);
            updateTransform();
        });

        wrapper.querySelector('.zoom-out').addEventListener('click', () => {
            scale = Math.max(scale / 1.2, 0.5);
            updateTransform();
        });

        wrapper.querySelector('.reset').addEventListener('click', () => {
            scale = 1;
            translate = { x: 0, y: 0 };
            updateTransform();
        });

        // Pan functionality
        mermaidDiv.addEventListener('mousedown', startPan);
        document.addEventListener('mousemove', pan);
        document.addEventListener('mouseup', endPan);

        function startPan(e) {
            panning = true;
            start = { x: e.clientX - translate.x, y: e.clientY - translate.y };
        }

        function pan(e) {
            if (!panning) return;
            e.preventDefault();
            translate = {
                x: e.clientX - start.x,
                y: e.clientY - start.y
            };
            updateTransform();
        }

        function endPan() {
            panning = false;
        }

        function updateTransform() {
            mermaidDiv.style.transform = `translate(${translate.x}px, ${translate.y}px) scale(${scale})`;
        }

        // Add mouse wheel zoom
        wrapper.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            scale = Math.max(0.5, Math.min(scale * delta, 3));
            updateTransform();
        });
    });
}); 