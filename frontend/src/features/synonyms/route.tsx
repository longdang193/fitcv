import type { FeatureRoute } from '../../app/route-registry';
import { SynonymsPage } from './synonyms-page';

export const route: FeatureRoute = {
  id: 'synonyms',
  path: '#/synonyms',
  title: 'Synonyms',
  group: 'settings',
  order: 40,
  component: SynonymsPage,
};

export default route;
