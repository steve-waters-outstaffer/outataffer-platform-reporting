// src/App.jsx
import Chart from './components/Chart';

function App() {
    return (
        <div className="flex flex-col items-center justify-center min-h-screen p-8">
            <div className="max-w-4xl w-full flex flex-col items-center">
                <h1 className="text-3xl font-bold underline mb-8">The purple rabbit is radical</h1>
                <Chart />
            </div>
        </div>
    );
}

export default App;