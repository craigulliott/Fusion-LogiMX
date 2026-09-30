// Bundles index.ts into dist/index.mjs and copies package/ (the plugin metadata)
// next to it. Adapted from the @logitech/plugin-toolkit JavaScript template.
// `--watch` also links dist/ into Logi Plugin Service and reloads the plugin
// after every rebuild; Ctrl+C unlinks it again.
import { postBuildProcessing, unlinkPlugin } from '@logitech/plugin-toolkit';
import { esmShimPlugin } from '@logitech/plugin-toolkit/esbuild';
import { build, context } from 'esbuild';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(fileURLToPath(import.meta.url));
const watch = process.argv.includes('--watch');

const config = {
  entryPoints: [resolve(root, 'index.ts')],
  outfile: resolve(root, 'dist', 'index.mjs'),
  bundle: true,
  platform: 'node',
  target: 'es2022',
  format: 'esm',
  logLevel: 'info',
  plugins: [
    esmShimPlugin({ require: true, globals: true }),
    {
      name: 'post-build',
      setup(b) {
        b.onEnd(async (result) => {
          if (result.errors.length === 0) await postBuildProcessing(root, watch);
        });
      },
    },
  ],
};

if (watch) {
  const ctx = await context(config);
  await ctx.watch();
  const stop = async () => {
    await unlinkPlugin(true).catch(() => {});
    await ctx.dispose();
    process.exit(0);
  };
  process.on('SIGINT', stop);
  process.on('SIGTERM', stop);
} else {
  await build(config);
}
