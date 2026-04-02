from __future__ import annotations

import logging

_LOGGER = logging.getLogger(__name__)

LEVEL1_TO_STN_ID = {
    "서울특별시": "109",
    "인천광역시": "109",
    "경기도": "109",
    "강원특별자치도": "105",
    "강원도": "105",
    "충청북도": "131",
    "충청남도": "133",
    "대전광역시": "133",
    "세종특별자치시": "133",
    "전북특별자치도": "146",
    "전라북도": "146",
    "전라남도": "156",
    "광주광역시": "156",
    "경상북도": "143",
    "대구광역시": "143",
    "경상남도": "159",
    "부산광역시": "159",
    "울산광역시": "159",
    "제주특별자치도": "184",
}

LEVEL1_TO_REG_ID = {
    "서울특별시": "11B10101",
    "인천광역시": "11B20201",
    "경기도": "11B20601",
    "강원특별자치도": "11D10301",
    "강원도": "11D10301",
    "충청북도": "11C10301",
    "충청남도": "11C20401",
    "대전광역시": "11C20401",
    "세종특별자치시": "11C20404",
    "전북특별자치도": "11F10201",
    "전라북도": "11F10201",
    "전라남도": "11F20501",
    "광주광역시": "11F20501",
    "경상북도": "11H10701",
    "대구광역시": "11H10701",
    "경상남도": "11H20201",
    "부산광역시": "11H20201",
    "울산광역시": "11H20101",
    "제주특별자치도": "11G00201",
}


def midterm_stn_id_for_region(level1: str | None) -> str:
    if not level1:
        _LOGGER.warning("midterm_stn_id_for_region: level1 is empty, using Seoul default (109)")
        return "108"
    stn_id = LEVEL1_TO_STN_ID.get(level1)
    if stn_id is None:
        _LOGGER.warning(
            "midterm_stn_id_for_region: unknown region '%s', using Seoul default (109)", level1
        )
        return "108"
    return stn_id


def midterm_reg_id_for_region(level1: str | None) -> str:
    if not level1:
        _LOGGER.warning("midterm_reg_id_for_region: level1 is empty, using Seoul default (11B10101)")
        return "11B10101"
    reg_id = LEVEL1_TO_REG_ID.get(level1)
    if reg_id is None:
        _LOGGER.warning(
            "midterm_reg_id_for_region: unknown region '%s', using Seoul default (11B10101)", level1
        )
        return "11B10101"
    return reg_id
