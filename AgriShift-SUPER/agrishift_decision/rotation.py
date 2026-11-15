"""Finite, explainable seasonal crop-sequence generator.

This is a crop-family screening heuristic, not a disease diagnosis. The crop
catalogue and planting windows are illustrative; the user controls eligible
crops, horizon, and whether to *strictly* reject adjacent families.
"""
from itertools import product
from datetime import date, timedelta


class RotationError(ValueError):
    """Invalid rotation specification or an infeasible set of choices."""


def seasonal_slots(planning_seasons, first_winter_year=2026):
    if planning_seasons not in (2, 4, 6):
        raise RotationError('Planning seasons must be 2, 4, or 6')
    return [
        {'slot': i + 1,
         'season': 'winter' if i % 2 == 0 else 'summer',
         'year': first_winter_year + i // 2 + (1 if i % 2 else 0),
         'anchor_year': first_winter_year + i // 2}
        for i in range(planning_seasons)
    ]


def generate_sequences(crop_catalog, planning_seasons, allowed_crops, previous_crop='unknown', strict_family_rotation=False,
                       first_winter_year=2026):
    """Return *all* valid ordered sequences and transparent pruning counts.

    Only adjacent same-family pairs are eliminated when strict is requested;
    without that setting they are retained and marked as a diversity concern.
    It is intentionally a user-selected rule, not a universal farming law.
    """
    if not isinstance(allowed_crops, (list, tuple)) or not allowed_crops:
        raise RotationError('Select at least one supported crop for each season')
    if len(set(allowed_crops)) != len(allowed_crops):
        raise RotationError('Crop choices cannot contain duplicates')
    unknown = set(allowed_crops).difference(crop_catalog)
    if unknown:
        raise RotationError('Unsupported crop(s): ' + ', '.join(sorted(unknown)))
    if previous_crop != 'unknown' and previous_crop not in crop_catalog:
        raise RotationError('Unsupported previous crop')
    slots = seasonal_slots(planning_seasons, first_winter_year)
    # Paddies require flooding/percolation management, and alfalfa's published
    # first-cut example is not a complete rotation season. Both remain available
    # in /api/crop-assessment with quantified atmospheric ETc.
    allowed_crops=[c for c in allowed_crops if crop_catalog[c].get('rotation_eligible',True)]
    candidates_per_slot = [tuple(c for c in allowed_crops if crop_catalog[c]['season'] == s['season']) for s in slots]
    if any(not pool for pool in candidates_per_slot):
        raise RotationError('Please select at least one winter crop AND one summer crop')
    raw_count = 1
    for pool in candidates_per_slot:
        raw_count *= len(pool)
    prev_family = crop_catalog[previous_crop]['family'] if previous_crop != 'unknown' else None
    def sowing(cid, slot):
        crop=crop_catalog[cid]
        m=crop.get('sowing_month', 11 if slot['season']=='winter' else 5)
        day=crop.get('sowing_day', 10 if slot['season']=='winter' else 15)
        return date(slot['anchor_year']+(1 if slot['season']=='summer' else 0),m,day)
    sequences = []
    calendar_excluded=0
    for seq in product(*candidates_per_slot):
        occupied=[(sowing(cid,slot),sowing(cid,slot)+timedelta(days=sum(crop_catalog[cid]['stages_days'])))
                  for cid,slot in zip(seq,slots)]
        if any(occupied[i][1]>occupied[i+1][0] for i in range(len(occupied)-1)):
            calendar_excluded+=1
            continue
        families = [crop_catalog[c]['family'] for c in seq]
        family_path = ([prev_family] if prev_family else []) + families
        if strict_family_rotation and any(a == b for a, b in zip(family_path, family_path[1:])):
            continue
        sequences.append(seq)
    return {
        'slots': slots,
        'sequences': sequences,
        'generated_count': raw_count,
        'excluded_family_rule_count': raw_count - calendar_excluded - len(sequences),
        'excluded_calendar_overlap_count':calendar_excluded,
        'valid_count': len(sequences),
        'choices_by_season': {
            'winter': [c for c in allowed_crops if crop_catalog[c]['season'] == 'winter'],
            'summer': [c for c in allowed_crops if crop_catalog[c]['season'] == 'summer']
        }
    }
