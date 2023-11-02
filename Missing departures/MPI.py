import time
import pandas as pd
from mpi4py import MPI

comm = MPI.COMM_WORLD
size = comm.Get_size()
rank = comm.Get_rank()


def GetMissingDates(reading_info: list):
    print(f'started processing chunk. ')
    start_time = time.time()
    df = pd.read_csv('../datasets/Combined_Flights_2021.csv', nrows=reading_info[0], skiprows=range(1, reading_info[1]))
    # Getting missing dates
    missing_dates = df[df.isna().any(axis=1)]

    if missing_dates.empty:
        print("Empty Chunk")
        return

    # Getting missing dates by flight date
    df_new = missing_dates.groupby(df['FlightDate'], as_index=False)

    # crunch them all and get their size
    combined = df_new.size()
    # Sort them by size
    combined.sort_values(by='size', ascending=False)

    end_time = time.time()
    print("Chunk time taken  : " + str(end_time - start_time))
    return combined


def GetTotalResults(results):
    processed_chunks = []
    for res in results:
        if res.empty:
            continue
        processed_chunks.append(res)

    merged_chunks = pd.concat(processed_chunks)
    merged_chunks.groupby(merged_chunks['FlightDate'], as_index=False).size()
    return merged_chunks.sort_values(by='size', ascending=False)


def main():
    slave_workers = size - 1
    rows = GetNumberOfRows()
    chunk_size = int(rows / slave_workers)
    print('using MPI....')

    start_time = time.time()
    chunk_distribution = distribute_rows(n_rows=chunk_size, n_processes=slave_workers)
    distributeTasks(chunk_distribution, size)

    results = GetResults()

    result = GetTotalResults(results)
    print(result)
    end_time = time.time()
    print("Total time of handling  : " + str(end_time - start_time))


def distribute_rows(n_rows: int, n_processes):
    reading_info = []
    skip_rows = 0
    reading_info.append([n_rows - skip_rows, skip_rows])
    skip_rows = n_rows

    for _ in range(1, n_processes - 1):
        reading_info.append([n_rows, skip_rows])
        skip_rows = skip_rows + n_rows

    reading_info.append([None, skip_rows])
    return reading_info


def GetNumberOfRows():
    return int(sum(1 for line in open('../datasets/Combined_Flights_2021.csv')))


def distributeTasks(distribution, size):
    for worker in range(1, size):
        chunk = worker - 1
        comm.send(distribution[chunk], dest=worker)


def GetResults():
    results = []
    for worker in (range(1, size)):  # receive
        result = comm.recv(source=worker)
        results.append(result)
        print(f'received from Worker slave {worker}')
    return results

if __name__ == "__main__":

    if rank == 0:
        main()
    elif rank > 0:
        chunk = comm.recv()
        (f'Worker {rank} is assigned chunk info {chunk}')
        result = GetMissingDates(chunk)
        print(f'Worker slave {rank} is done. Sending back to master')
        comm.send(result, dest=0)
