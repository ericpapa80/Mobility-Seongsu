"""VWorld scraper configuration."""

import os
from typing import Dict, List, Optional
from config.settings import settings

# 토지·건물 레이어는 모두 WFS로 요청 (Data API 대신). PROPERTYNAME으로 속성 명시.

# 도로명주소건물(lt_c_spbd) WFS 속성 목록 (실제 API 가능 목록 기준, gid 미지원)
LT_C_SPBD_PROPERTY_NAMES: List[str] = [
    "pk", "bd_mgt_sn", "sido", "sigungu", "gu", "rd_nm", "bld_s", "bld_e",
    "buld_nm", "buld_nm_dc", "buld_se_cd", "bul_eng_nm", "zip_cd", "gro_flo_co", "und_flo_co",
    "buld_no", "sig_cd", "rn_cd", "emd_cd", "pnu", "xpos", "ypos", "poi_chk", "ag_geom",
]

# LX맵(lt_c_landinfobasemap, 토지) WFS 속성 목록 (실제 API 가능 목록 기준, gid 미지원)
LT_C_LANDINFOBASEMAP_PROPERTY_NAMES: List[str] = [
    "pnu", "sido_cd", "sido_nm", "sgg_cd", "sgg_nm", "emd_cd", "emd_nm", "ri_cd", "ri_nm",
    "gbn_cd", "gbn_nm", "mnnm", "slno", "jibun", "jimok", "parea", "owner_cd", "owner_nm",
    "shr_cnt", "movde", "jiga_ilp", "jiga_std_y", "rn_cd", "rn_nm", "bld_mnnm", "bld_slno",
    "bld_nm", "bldrgst_pk", "ufid", "rgsde", "ag_geom",
]

# WFS로 수집하는 레이어와 해당 PROPERTYNAME 목록
WFS_LAYER_PROPERTY_NAMES: Dict[str, List[str]] = {
    "LT_C_SPBD": LT_C_SPBD_PROPERTY_NAMES,
    "LT_C_LANDINFOBASEMAP": LT_C_LANDINFOBASEMAP_PROPERTY_NAMES,
}


class VWorldConfig:
    """Configuration for VWorld scraper."""
    
    @staticmethod
    def get_base_url() -> str:
        """Get VWorld base URL."""
        return os.getenv("VWORLD_BASE_URL", "https://api.vworld.kr")
    
    @staticmethod
    def get_api_key() -> str:
        """Get VWorld API key."""
        return os.getenv("VWORLD_API_KEY", "")
    
    @staticmethod
    def get_domain() -> str:
        """Get VWorld domain."""
        return os.getenv("vworld_domain", os.getenv("VWORLD_DOMAIN", "http://localhost"))
    
    @staticmethod
    def get_data_api_url() -> str:
        """Get VWorld Data API URL."""
        return f"{VWorldConfig.get_base_url()}/req/data"
    
    @staticmethod
    def get_wfs_api_url() -> str:
        """Get VWorld WFS API URL."""
        return f"{VWorldConfig.get_base_url()}/req/wfs"
    
    @staticmethod
    def get_credentials() -> Dict[str, str]:
        """Get VWorld credentials as dictionary."""
        return {
            'api_key': VWorldConfig.get_api_key(),
            'domain': VWorldConfig.get_domain()
        }
    
    @staticmethod
    def validate() -> bool:
        """Validate VWorld configuration."""
        if not VWorldConfig.get_api_key():
            return False
        if not VWorldConfig.get_domain():
            return False
        return True
