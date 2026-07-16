"use client";

/**
 * The Organism Lens renderer — the only module in the app that imports three.
 * It is loaded through `next/dynamic({ ssr: false })` and mounted only once the
 * observer opens the Lens, so three never reaches the bundle of a page that
 * merely links to a species.
 *
 * The body is a readout of the model, not art: every dimension comes from
 * `deriveBodyParams`, and the coil follows `species.chirality`, so the hand a
 * lineage carries is visible directly (docs/CHIRALITY_AND_MIND.md §8).
 */

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import type { BodyParams, FormState, LensMode } from "@/lib/organismLens";

type OrganismLensCanvasProps = {
  body: BodyParams;
  form: FormState;
  mode: LensMode;
  /** Tints the organism so lineages stay distinguishable at a glance. */
  hue: number;
};

/** Points along the coiled spine, in the lineage's own hand. */
function spinePoints(body: BodyParams, form: FormState): THREE.Vector3[] {
  const points: THREE.Vector3[] = [];
  const steps = Math.max(24, body.segments * 6);
  // A committed lineage coils; an uncommitted one (chirality 0) stays straight —
  // no hand, no helix.
  const turns = body.coilDirection === 0 ? 0 : body.coilTurns;
  // Load twists the body against its own coil: the form fights itself (§6.3).
  const counter = 1 - form.counterTwist * 1.6;

  for (let i = 0; i <= steps; i += 1) {
    const t = i / steps;
    const angle = t * turns * Math.PI * 2 * body.coilDirection * counter;
    // Taper narrows the coil toward the tail.
    const spread = (1 - t * body.taper) * body.radius;
    points.push(
      new THREE.Vector3(
        Math.cos(angle) * spread,
        (t - 0.5) * 3.2,
        Math.sin(angle) * spread * (0.6 + body.symmetry * 0.4)
      )
    );
  }
  return points;
}

function buildOrganism(body: BodyParams, form: FormState, hue: number): THREE.Group {
  const group = new THREE.Group();
  const points = spinePoints(body, form);
  const curve = new THREE.CatmullRomCurve3(points);

  const coherent = new THREE.Color().setHSL(hue / 360, 0.55, 0.55);
  const strained = new THREE.Color().setHSL(0.02, 0.7, 0.45);
  // A failing form drains toward a bruised red rather than staying pretty.
  const bodyColor = coherent.clone().lerp(strained, form.counterTwist);

  const coreMaterial = new THREE.MeshStandardMaterial({
    color: bodyColor,
    roughness: 0.45,
    metalness: 0.12,
    flatShading: body.symmetry < 0.6
  });

  const core = new THREE.Mesh(
    new THREE.TubeGeometry(curve, body.segments * 5, body.radius * 0.34, 10, false),
    coreMaterial
  );
  group.add(core);

  // Segment rings — the vertebrae you can count.
  const ringMaterial = new THREE.MeshStandardMaterial({
    color: bodyColor.clone().offsetHSL(0, 0, 0.16),
    roughness: 0.6
  });
  for (let i = 0; i < body.segments; i += 1) {
    const t = (i + 0.5) / body.segments;
    const at = curve.getPointAt(t);
    const tangent = curve.getTangentAt(t);
    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(body.radius * 0.42 * (1 - t * body.taper * 0.6), 0.022, 6, 16),
      ringMaterial
    );
    ring.position.copy(at);
    ring.lookAt(at.clone().add(tangent));
    group.add(ring);
  }

  // Paired appendages, spaced along the spine.
  if (body.limbs > 0) {
    const limbMaterial = new THREE.MeshStandardMaterial({
      color: bodyColor.clone().offsetHSL(0, -0.1, -0.08),
      roughness: 0.7
    });
    const pairs = body.limbs / 2;
    for (let i = 0; i < pairs; i += 1) {
      const t = 0.15 + (i / Math.max(1, pairs - 1 || 1)) * 0.7;
      const at = curve.getPointAt(Math.min(0.95, t));
      for (const side of [-1, 1]) {
        const limb = new THREE.Mesh(
          new THREE.CapsuleGeometry(0.026, body.limbLength * 0.9, 3, 6),
          limbMaterial
        );
        limb.position.copy(at);
        // Asymmetry rises as symmetry falls — a lopsided lineage looks lopsided.
        const skew = (1 - body.symmetry) * 0.5;
        limb.position.x += side * (body.radius * 0.5 + body.limbLength * 0.4);
        limb.position.y += (side > 0 ? skew : -skew) * 0.3;
        limb.rotation.z = side * (Math.PI / 2.6);
        group.add(limb);
      }
    }
  }

  return group;
}

/** Free every GPU resource this group holds — three does not do it for you. */
function disposeGroup(group: THREE.Group): void {
  group.traverse((child) => {
    const mesh = child as THREE.Mesh;
    if (mesh.geometry) {
      mesh.geometry.dispose();
    }
    const material = mesh.material as THREE.Material | THREE.Material[] | undefined;
    if (Array.isArray(material)) {
      material.forEach((item) => item.dispose());
    } else if (material) {
      material.dispose();
    }
  });
}

export default function OrganismLensCanvas({ body, form, mode, hue }: OrganismLensCanvasProps) {
  const shellRef = useRef<HTMLDivElement | null>(null);
  const [failed, setFailed] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(media.matches);
    const onChange = (event: MediaQueryListEvent) => setReducedMotion(event.matches);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    const shell = shellRef.current;
    if (!shell) {
      return;
    }

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch {
      // No WebGL (old hardware, blocked context): the caller keeps the 2D field.
      setFailed(true);
      return;
    }

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
    camera.position.set(0, 0, 5.4);

    scene.add(new THREE.AmbientLight(0xffffff, 1.5));
    const key = new THREE.DirectionalLight(0xffffff, 2.2);
    key.position.set(3, 4, 5);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x88aaff, 1.1);
    rim.position.set(-4, -2, -3);
    scene.add(rim);

    const organism = buildOrganism(body, form, hue);
    scene.add(organism);

    shell.appendChild(renderer.domElement);

    function resize() {
      const width = shell?.clientWidth ?? 0;
      const height = shell?.clientHeight ?? 0;
      if (width === 0 || height === 0) {
        return;
      }
      // Browser zoom moves devicePixelRatio, so the ratio is set here rather
      // than once at mount — otherwise the backing store drifts from the canvas.
      renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
      // `false`: the backing store is ours, the display size is CSS's (see
      // .lens-stage canvas). Passing true would fight the stylesheet.
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    }
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(shell);

    let frame = 0;
    let elapsed = 0;
    let last = performance.now();

    function draw(now: number) {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      elapsed += dt;
      // A strained lineage never settles; a coherent one turns evenly.
      organism.rotation.y += dt * (0.35 + form.jitter * 0.9);
      organism.rotation.x = Math.sin(elapsed * 0.6) * 0.08 * (1 + form.jitter * 3);
      renderer.render(scene, camera);
      frame = window.requestAnimationFrame(draw);
    }

    if (reducedMotion) {
      // Honour the user's setting: render one still frame, never animate.
      renderer.render(scene, camera);
    } else {
      frame = window.requestAnimationFrame(draw);
    }

    return () => {
      window.cancelAnimationFrame(frame);
      observer.disconnect();
      disposeGroup(organism);
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [body, form, hue, reducedMotion]);

  if (failed) {
    return (
      <p className="lens-fallback">
        This device cannot open a 3D view. The distribution field above still tracks this
        lineage.
      </p>
    );
  }

  return (
    <div className="lens-stage" ref={shellRef} role="img" aria-label={organismLabel(body, mode)} />
  );
}

function organismLabel(body: BodyParams, mode: LensMode): string {
  const hand = body.coilDirection === 0 ? "unhanded" : body.coilDirection > 0 ? "right" : "left";
  return `A ${hand}-coiled organism with ${body.segments} segments and ${body.limbs} appendages, rendered in ${mode} mode.`;
}
