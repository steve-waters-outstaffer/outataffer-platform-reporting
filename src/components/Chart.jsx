// src/components/Chart.jsx
import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

const EChartsComponent = ({ option, style = { height: '400px', width: '100%' } }) => {
    const chartRef = useRef(null);
    let chartInstance = null;

    useEffect(() => {
        if (chartRef.current) {
            chartInstance = echarts.init(chartRef.current);
            chartInstance.setOption(option);
        }

        const resizeHandler = () => {
            chartInstance?.resize();
        };

        window.addEventListener('resize', resizeHandler);

        return () => {
            chartInstance?.dispose();
            window.removeEventListener('resize', resizeHandler);
        };
    }, [option]);

    return <div ref={chartRef} style={style} />;
};

export default EChartsComponent;
